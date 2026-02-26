import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

from app.agents.librarian.graph import librarian_graph
from app.agents.state import build_librarian_initial_state
from app.config.auth import get_user_id
from app.config.dependencies import get_diary_scrap_link_repository, get_scrap_service
from app.repositories.diary_scrap_link_repository import DiaryScrapLinkRepository
from app.schemas.diary_schema import LinkedDiariesResponse, LinkedDiaryItem
from app.schemas.scrap_schema import (
    BulkActionRequest,
    BulkActionResponse,
    ScrapCreate,
    ScrapCreateResponse,
    ScrapDetail,
    ScrapListItem,
    ScrapListResponse,
    ScrapUpdate,
)
from app.services.ingest_service import process_note_content, process_pdf_content, process_web_content
from app.services.scrap_service import ScrapService

logger = logging.getLogger(__name__)

# PDF 파일 업로드 최대 크기 (20MB)
MAX_PDF_FILE_SIZE_BYTES = 20 * 1024 * 1024

router = APIRouter(prefix="/scraps", tags=["scraps"])


async def _process_with_librarian(
    scrap_id: str,
    content: str,
    user_id: str,
) -> None:
    """백그라운드 태스크: Librarian 에이전트로 분류, 태깅, 엔티티 추출."""
    try:
        initial_state = build_librarian_initial_state(scrap_id, content, user_id)
        result = await librarian_graph.ainvoke(initial_state)
        logger.info(
            "Librarian processed scrap %s: classification=%s",
            scrap_id,
            result.get("classification"),
        )
    except Exception:
        logger.exception("Librarian error for scrap %s", scrap_id)


@router.post("", response_model=ScrapCreateResponse, status_code=201)
async def create_scrap(
    data: ScrapCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
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
                detail="PDF must be uploaded via POST /scraps/upload-pdf",
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

        scrap = await scrap_service.create_scrap(
            user_id=user_id,
            title=processed["title"],
            content=processed["content"],
            source_type=data.source_type,
            source_url=processed.get("source_url"),
        )

        background_tasks.add_task(
            _process_with_librarian,
            str(scrap.id),
            processed["content"],
            str(user_id),
        )

        return ScrapCreateResponse(id=scrap.id, status="processing")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/upload-pdf", response_model=ScrapCreateResponse, status_code=201)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """PDF 파일 업로드 및 수집."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_PDF_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")

        processed = await process_pdf_content(file_bytes, file.filename)

        scrap = await scrap_service.create_scrap(
            user_id=user_id,
            title=processed["title"],
            content=processed["content"],
            source_type="PDF",
            source_url=None,
        )

        background_tasks.add_task(
            _process_with_librarian,
            str(scrap.id),
            processed["content"],
            str(user_id),
        )

        return ScrapCreateResponse(id=scrap.id, status="processing")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/backfill", status_code=200)
async def backfill_scraps(
    background_tasks: BackgroundTasks,
    force: bool = Query(False),
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """기존 스크랩을 Librarian 파이프라인으로 재처리. force=true 시 전체 재처리."""
    items, total = await scrap_service.list_scraps(user_id=user_id, page=1, limit=100)

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
async def reprocess_all_scraps(
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """모든 스크랩을 Librarian 파이프라인으로 재처리 (그래프 백필용)."""
    page = 1
    queued = 0
    total = 0
    while True:
        items, count = await scrap_service.list_scraps(user_id=user_id, page=page, limit=100)
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
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """스크랩 일괄 작업 (삭제, 태그 추가, 태그 제거). 최대 50개."""
    if data.action in ("add_tags", "remove_tags") and not data.tags:
        raise HTTPException(status_code=400, detail="tags field is required for tag actions")

    affected = await scrap_service.bulk_action(
        action=data.action,
        scrap_ids=data.scrap_ids,
        user_id=user_id,
        tags=data.tags,
    )
    return BulkActionResponse(affected=affected)


@router.get("", response_model=ScrapListResponse)
async def list_scraps(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    tags: str | None = Query(None, description="쉼표 구분 태그 필터"),
    source_type: str | None = Query(None, description="소스 타입 필터 (WEB, PDF, NOTE 등)"),
    date_from: str | None = Query(None, description="시작일 (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="종료일 (YYYY-MM-DD)"),
    sort_by: str = Query("created_at", description="정렬 기준 (created_at, updated_at, title)"),
    sort_order: str = Query("desc", description="정렬 방향 (asc, desc)"),
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """페이지네이션된 스크랩 목록 조회 (필터 + 정렬 지원)."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    items, total = await scrap_service.list_scraps(
        user_id=user_id,
        page=page,
        limit=limit,
        search=search,
        tags=tag_list,
        source_type=source_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ScrapListResponse(
        items=[
            ScrapListItem(
                id=item.id,
                title=item.title,
                summary=item.summary,
                source_type=item.source_type,
                tags=item.tags or [],
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
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """사용자의 기존 태그 목록 조회 (자동완성용)."""
    return await scrap_service.get_user_tags(user_id, q)


@router.get("/{scrap_id}/diaries", response_model=LinkedDiariesResponse)
async def get_scrap_diaries(
    scrap_id: UUID,
    user_id: UUID = Depends(get_user_id),
    link_repo: DiaryScrapLinkRepository = Depends(get_diary_scrap_link_repository),
):
    """해당 스크랩을 참조한 다이어리 목록 역참조 조회."""
    try:
        rows = await link_repo.get_diaries_by_scrap(scrap_id)
        items = []
        for row in rows:
            diary_data = row.get("diaries")
            if not diary_data:
                continue
            content = diary_data.get("content", "")
            # 미리보기: 첫 80자
            preview = content[:80].replace("\n", " ").strip()
            if len(content) > 80:
                preview += "..."
            items.append(
                LinkedDiaryItem(
                    diary_id=diary_data["id"],
                    date=diary_data.get("created_at", "")[:10],
                    preview=preview,
                    mood=diary_data.get("mood"),
                    link_type=row.get("link_type", "manual"),
                )
            )
        return LinkedDiariesResponse(diaries=items)
    except Exception:
        logger.exception("스크랩 역참조 다이어리 조회 실패 (scrap_id=%s)", scrap_id)
        return LinkedDiariesResponse(diaries=[])


@router.get("/{scrap_id}", response_model=ScrapDetail)
async def get_scrap(
    scrap_id: UUID,
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """ID로 단일 스크랩 상세 조회."""
    scrap = await scrap_service.get_scrap(scrap_id, user_id)

    if not scrap:
        raise HTTPException(status_code=404, detail="Scrap not found")

    return ScrapDetail(
        id=scrap.id,
        title=scrap.title,
        content=scrap.content,
        summary=scrap.summary,
        source_url=scrap.source_url,
        source_type=scrap.source_type,
        tags=scrap.tags,
        created_at=scrap.created_at,
        updated_at=scrap.updated_at,
    )


@router.patch("/{scrap_id}", response_model=ScrapDetail)
async def update_scrap(
    scrap_id: UUID,
    data: ScrapUpdate,
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """스크랩 제목, 요약, 태그 수정."""
    updated = await scrap_service.update_scrap(
        scrap_id=scrap_id,
        user_id=user_id,
        title=data.title,
        summary=data.summary,
        tags=data.tags,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Scrap not found")

    return ScrapDetail(
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


@router.delete("/{scrap_id}", status_code=204)
async def delete_scrap(
    scrap_id: UUID,
    user_id: UUID = Depends(get_user_id),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """ID로 스크랩 삭제."""
    success = await scrap_service.delete_scrap(scrap_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Scrap not found")

    return None
