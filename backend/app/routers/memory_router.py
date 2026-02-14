import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

from app.agents.librarian.graph import librarian_graph
from app.agents.state import build_librarian_initial_state
from app.config.auth import get_user_id
from app.config.dependencies import get_journal_memory_link_repository, get_memory_service
from app.repositories.journal_memory_link_repository import JournalMemoryLinkRepository
from app.schemas.journal_schema import LinkedJournalItem, LinkedJournalsResponse
from app.schemas.memory_schema import (
    BulkActionRequest,
    BulkActionResponse,
    MemoryCreate,
    MemoryCreateResponse,
    MemoryDetail,
    MemoryListItem,
    MemoryListResponse,
    MemoryUpdate,
)
from app.services.ingest_service import process_note_content, process_pdf_content, process_web_content
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# PDF 파일 업로드 최대 크기 (20MB)
MAX_PDF_FILE_SIZE_BYTES = 20 * 1024 * 1024

router = APIRouter(prefix="/memories", tags=["memories"])


async def _process_with_librarian(
    memory_id: str,
    content: str,
    user_id: str,
) -> None:
    """백그라운드 태스크: Librarian 에이전트로 분류, 태깅, 엔티티 추출."""
    try:
        initial_state = build_librarian_initial_state(memory_id, content, user_id)
        result = await librarian_graph.ainvoke(initial_state)
        logger.info(
            "Librarian processed memory %s: classification=%s",
            memory_id,
            result.get("classification"),
        )
    except Exception:
        logger.exception("Librarian error for memory %s", memory_id)


@router.post("", response_model=MemoryCreateResponse, status_code=201)
async def create_memory(
    data: MemoryCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """새 콘텐츠(URL 또는 노트) 수집 및 저장."""
    try:
        if data.source_type == "WEB":
            if not data.url:
                raise HTTPException(status_code=400, detail="URL is required for WEB type")
            processed = await process_web_content(data.url)
            # Extension이 본문을 직접 전송한 경우 병합
            if data.content:
                processed["content"] = data.content + "\n\n" + processed["content"]
            if data.memo and data.memo != processed["title"]:
                processed["content"] = f"[메모] {data.memo}\n\n" + processed["content"]

        elif data.source_type == "PDF":
            raise HTTPException(
                status_code=400,
                detail="PDF must be uploaded via POST /memories/upload-pdf",
            )

        elif data.source_type == "NOTE":
            if not data.content:
                raise HTTPException(status_code=400, detail="Content is required for NOTE type")
            processed = await process_note_content(data.content, data.memo)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown source type: {data.source_type}",
            )

        memory = await memory_service.create_memory(
            user_id=user_id,
            title=processed["title"],
            content=processed["content"],
            source_type=data.source_type,
            source_url=processed.get("source_url"),
        )

        background_tasks.add_task(
            _process_with_librarian,
            str(memory.id),
            processed["content"],
            str(user_id),
        )

        return MemoryCreateResponse(id=memory.id, status="processing")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/upload-pdf", response_model=MemoryCreateResponse, status_code=201)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """PDF 파일 업로드 및 수집."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_PDF_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")

        processed = await process_pdf_content(file_bytes, file.filename)

        memory = await memory_service.create_memory(
            user_id=user_id,
            title=processed["title"],
            content=processed["content"],
            source_type="PDF",
            source_url=None,
        )

        background_tasks.add_task(
            _process_with_librarian,
            str(memory.id),
            processed["content"],
            str(user_id),
        )

        return MemoryCreateResponse(id=memory.id, status="processing")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/backfill", status_code=200)
async def backfill_memories(
    background_tasks: BackgroundTasks,
    force: bool = Query(False),
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """기존 메모리를 Librarian 파이프라인으로 재처리. force=true 시 전체 재처리."""
    items, total = await memory_service.list_memories(user_id=user_id, page=1, limit=100)

    queued = 0
    for item in items:
        if not force and item.tags is not None:
            continue
        background_tasks.add_task(
            _process_with_librarian,
            str(item.id),
            item.content,
            str(user_id),
        )
        queued += 1

    return {"queued": queued, "total": total}


@router.post("/reprocess-all", status_code=200)
async def reprocess_all_memories(
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """모든 메모리를 Librarian 파이프라인으로 재처리 (그래프 백필용)."""
    page = 1
    queued = 0
    total = 0
    while True:
        items, count = await memory_service.list_memories(user_id=user_id, page=page, limit=100)
        total = count
        if not items:
            break
        for item in items:
            background_tasks.add_task(
                _process_with_librarian,
                str(item.id),
                item.content,
                str(user_id),
            )
            queued += 1
        if queued >= total:
            break
        page += 1

    return {"queued": queued, "total": total}


@router.post("/bulk", response_model=BulkActionResponse)
async def bulk_action(
    data: BulkActionRequest,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """메모리 일괄 작업 (삭제, 태그 추가, 태그 제거). 최대 50개."""
    if data.action in ("add_tags", "remove_tags") and not data.tags:
        raise HTTPException(status_code=400, detail="tags field is required for tag actions")

    affected = await memory_service.bulk_action(
        action=data.action,
        memory_ids=data.memory_ids,
        user_id=user_id,
        tags=data.tags,
    )
    return BulkActionResponse(affected=affected)


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """페이지네이션된 메모리 목록 조회."""
    items, total = await memory_service.list_memories(
        user_id=user_id,
        page=page,
        limit=limit,
        search=search,
    )

    return MemoryListResponse(
        items=[
            MemoryListItem(
                id=item.id,
                title=item.title,
                summary=item.summary,
                source_type=item.source_type,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
    )


@router.get("/tags", response_model=list[str])
async def get_tags(
    q: str = Query("", description="태그 prefix 필터"),
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """사용자의 기존 태그 목록 조회 (자동완성용)."""
    return await memory_service.get_user_tags(user_id, q)


@router.get("/{memory_id}/journals", response_model=LinkedJournalsResponse)
async def get_memory_journals(
    memory_id: UUID,
    user_id: UUID = Depends(get_user_id),
    link_repo: JournalMemoryLinkRepository = Depends(get_journal_memory_link_repository),
):
    """해당 메모리를 참조한 저널 목록 역참조 조회."""
    try:
        rows = await link_repo.get_journals_by_memory(memory_id)
        items = []
        for row in rows:
            journal_data = row.get("journals")
            if not journal_data:
                continue
            content = journal_data.get("content", "")
            # 미리보기: 첫 80자
            preview = content[:80].replace("\n", " ").strip()
            if len(content) > 80:
                preview += "..."
            items.append(
                LinkedJournalItem(
                    journal_id=journal_data["id"],
                    date=journal_data.get("created_at", "")[:10],
                    preview=preview,
                    mood=journal_data.get("mood"),
                    link_type=row.get("link_type", "manual"),
                )
            )
        return LinkedJournalsResponse(journals=items)
    except Exception:
        logger.exception("메모리 역참조 저널 조회 실패 (memory_id=%s)", memory_id)
        return LinkedJournalsResponse(journals=[])


@router.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(
    memory_id: UUID,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """ID로 단일 메모리 상세 조회."""
    memory = await memory_service.get_memory(memory_id, user_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryDetail(
        id=memory.id,
        title=memory.title,
        content=memory.content,
        summary=memory.summary,
        source_url=memory.source_url,
        source_type=memory.source_type,
        tags=memory.tags,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


@router.patch("/{memory_id}", response_model=MemoryDetail)
async def update_memory(
    memory_id: UUID,
    data: MemoryUpdate,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """메모리 제목, 요약, 태그 수정."""
    updated = await memory_service.update_memory(
        memory_id=memory_id,
        user_id=user_id,
        title=data.title,
        summary=data.summary,
        tags=data.tags,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryDetail(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        summary=updated.summary,
        source_url=updated.source_url,
        source_type=updated.source_type,
        tags=updated.tags,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """ID로 메모리 삭제."""
    success = await memory_service.delete_memory(memory_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return None
