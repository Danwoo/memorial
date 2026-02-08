"""
Memory API Endpoints
Based on API_Spec.md - Section 3

Handles:
- POST /memories - Ingest new content
- GET /memories - List memories
- GET /memories/{id} - Get single memory
- DELETE /memories/{id} - Delete memory
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Optional
from uuid import UUID
import httpx

from app.schemas.memory import (
    MemoryCreate,
    MemoryCreateResponse,
    MemoryListResponse,
    MemoryListItem,
    MemoryDetail
)
from app.crud import crud_memory
from app.services import ingest_service
from app.core.supabase import get_supabase
from supabase import Client

router = APIRouter(prefix="/memories", tags=["memories"])

# TODO: Replace with actual user from JWT token
MOCK_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.post("", response_model=MemoryCreateResponse, status_code=201)
async def create_memory(
    data: MemoryCreate,
    background_tasks: BackgroundTasks,
    db: Client = Depends(get_supabase)
):
    """
    Ingest new content (URL or Note).
    
    - For WEB/PDF: Fetches and parses the URL
    - For NOTE: Saves raw content directly
    
    Returns immediately with 'processing' status.
    Background task will complete the processing.
    """
    try:
        # Process based on source type
        if data.source_type == "WEB":
            if not data.url:
                raise HTTPException(status_code=400, detail="URL is required for WEB type")
            
            processed = await ingest_service.process_web_content(data.url)
            
        elif data.source_type == "PDF":
            # TODO: Implement PDF parsing with Upstage API
            raise HTTPException(status_code=501, detail="PDF parsing not implemented yet")
            
        elif data.source_type == "NOTE":
            if not data.content:
                raise HTTPException(status_code=400, detail="Content is required for NOTE type")
            
            processed = await ingest_service.process_note_content(data.content, data.memo)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown source type: {data.source_type}")
        
        # Save to database
        memory = await crud_memory.create_memory(
            db=db,
            user_id=MOCK_USER_ID,
            title=processed["title"],
            content=processed["content"],
            source_type=data.source_type,
            source_url=processed.get("source_url")
        )
        
        # TODO: Add background task to trigger Librarian agent
        # background_tasks.add_task(process_with_librarian, memory.id)
        
        return MemoryCreateResponse(id=memory.id, status="processing")
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: Client = Depends(get_supabase)
):
    """
    Get paginated list of memories.
    Supports simple text search in title/content.
    """
    items, total = await crud_memory.get_memories_by_user(
        db=db,
        user_id=MOCK_USER_ID,
        page=page,
        limit=limit,
        search=search
    )
    
    return MemoryListResponse(
        items=[
            MemoryListItem(
                id=item.id,
                title=item.title,
                summary=item.summary,
                source_type=item.source_type,
                created_at=item.created_at
            )
            for item in items
        ],
        total=total
    )


@router.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(
    memory_id: UUID,
    db: Client = Depends(get_supabase)
):
    """
    Get single memory by ID.
    """
    memory = await crud_memory.get_memory_by_id(
        db=db,
        memory_id=memory_id,
        user_id=MOCK_USER_ID
    )
    
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
        updated_at=memory.updated_at
    )


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    db: Client = Depends(get_supabase)
):
    """
    Delete a memory by ID.
    Also removes associated Graph data (TODO).
    """
    success = await crud_memory.delete_memory(
        db=db,
        memory_id=memory_id,
        user_id=MOCK_USER_ID
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # TODO: Also delete from Neo4j graph
    
    return None
