"""
Search Router
API endpoints for semantic search
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.config.auth import get_user_id
from app.config.dependencies import get_search_service
from app.schemas.search_schema import RelatedMemory, SearchResponse, SearchResult
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def advanced_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.3, ge=0, le=1),
    source_type: str | None = Query(None, description="Filter by source type: WEB, PDF, NOTE"),
    days: int | None = Query(None, description="Filter by last N days"),
    tags: str | None = Query(None, description="Comma-separated tags to filter"),
    user_id: UUID = Depends(get_user_id),
    search_service: SearchService = Depends(get_search_service),
):
    """Advanced semantic search with filtering options."""
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    result = await search_service.search(
        user_id=user_id,
        query=q,
        limit=limit,
        threshold=threshold,
        source_type=source_type,
        days=days,
        tags=tag_list,
    )

    return SearchResponse(
        query=result["query"],
        results=[SearchResult(**r) for r in result["results"]],
        total=result["total"],
        filters_applied=result["filters_applied"],
    )


@router.get("/related/{memory_id}", response_model=list[RelatedMemory])
async def get_related_memories(
    memory_id: str,
    limit: int = Query(5, ge=1, le=20),
    user_id: UUID = Depends(get_user_id),
    search_service: SearchService = Depends(get_search_service),
):
    """Get memories related to a specific memory."""
    related = await search_service.get_related_memories(user_id, memory_id, limit)
    return [RelatedMemory(**r) for r in related]
