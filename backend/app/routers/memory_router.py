"""
Memory Router
API endpoints for memory operations
"""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

from app.agents.librarian.graph import librarian_graph
from app.config.auth import get_user_id
from app.config.dependencies import get_memory_service
from app.schemas.memory_schema import (
    MemoryCreate,
    MemoryCreateResponse,
    MemoryDetail,
    MemoryListItem,
    MemoryListResponse,
)
from app.services.ingest_service import process_note_content, process_pdf_content, process_web_content
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

MAX_PDF_FILE_SIZE_BYTES = 20 * 1024 * 1024

router = APIRouter(prefix="/memories", tags=["memories"])


def _build_librarian_initial_state(
    memory_id: str,
    content: str,
    user_id: str,
) -> dict:
    return {
        "messages": [],
        "user_id": user_id,
        "context": {},
        "target_memory_id": memory_id,
        "target_text": content,
        "classification": None,
        "summary": None,
        "tags": None,
        "extracted_entities": None,
        "extracted_relations": None,
        "is_streaming": False,
        "next_step": None,
        "error": None,
    }


async def _process_with_librarian(
    memory_id: str,
    content: str,
    user_id: str,
) -> None:
    """Background task: classify, tag, extract entities via Librarian agent."""
    try:
        initial_state = _build_librarian_initial_state(memory_id, content, user_id)

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
    """Ingest new content (URL or Note)."""
    try:
        if data.source_type == "WEB":
            if not data.url:
                raise HTTPException(status_code=400, detail="URL is required for WEB type")
            processed = await process_web_content(data.url)

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
    """Upload and ingest a PDF file."""
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
    """Re-process memories through Librarian pipeline. Use force=true to re-process all."""
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
    """Re-process ALL memories through Librarian pipeline (for graph backfill)."""
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


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Get paginated list of memories."""
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


@router.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(
    memory_id: UUID,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Get single memory by ID."""
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


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    user_id: UUID = Depends(get_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Delete a memory by ID."""
    success = await memory_service.delete_memory(memory_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return None
