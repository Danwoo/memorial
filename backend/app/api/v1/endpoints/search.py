"""
Search API Endpoints
Advanced semantic search with filters and recommendations
"""
from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime, timedelta

from app.services.vector_store import vector_store
from app.core.supabase import get_supabase_client
from app.schemas.search import SearchResult, SearchResponse, RelatedMemory

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def advanced_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.3, ge=0, le=1),
    source_type: Optional[str] = Query(None, description="Filter by source type: WEB, PDF, NOTE"),
    days: Optional[int] = Query(None, description="Filter by last N days"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter")
):
    """
    Advanced semantic search with filtering options.
    
    - **q**: Natural language query
    - **limit**: Maximum number of results
    - **threshold**: Minimum similarity score (0-1)
    - **source_type**: Filter by WEB, PDF, or NOTE
    - **days**: Only show results from last N days
    - **tags**: Comma-separated list of tags to filter
    """
    # Build filters
    filters = {}
    filters_applied = {}
    
    if source_type:
        filters["source_type"] = source_type
        filters_applied["source_type"] = source_type
    
    if days:
        filters_applied["days"] = days
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        filters_applied["tags"] = tag_list
    
    # Perform vector search
    results = await vector_store.similarity_search(
        query=q,
        limit=limit * 2,  # Get more results for filtering
        threshold=threshold,
        filters=filters if filters else None
    )
    
    search_results = []
    now = datetime.utcnow()
    
    for r in results:
        # Apply time filter if specified
        if days:
            created_at_str = r.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if (now - created_at) > timedelta(days=days):
                        continue
                except Exception:
                    pass
        
        # Apply tag filter if specified
        if tags:
            memory_tags = r.get("tags") or []
            if not any(t in memory_tags for t in tag_list):
                continue
        
        search_results.append(SearchResult(
            id=str(r.get("id", "")),
            title=r.get("title", "Untitled"),
            content=r.get("content", "")[:500],
            summary=r.get("summary"),
            source_type=r.get("source_type", "NOTE"),
            similarity=r.get("similarity", 0),
            created_at=r.get("created_at"),
            tags=r.get("tags")
        ))
        
        if len(search_results) >= limit:
            break
    
    return SearchResponse(
        query=q,
        results=search_results,
        total=len(search_results),
        filters_applied=filters_applied
    )


@router.get("/related/{memory_id}")
async def get_related_memories(
    memory_id: str,
    limit: int = Query(5, ge=1, le=20)
) -> List[RelatedMemory]:
    """
    Get memories related to a specific memory.
    Uses the memory's content to find similar items.
    """
    db = get_supabase_client()
    
    # Get the source memory
    result = db.table("memories").select("content, title").eq("id", memory_id).single().execute()
    
    if not result.data:
        return []
    
    source_content = result.data.get("content", "")
    source_title = result.data.get("title", "")
    
    # Search for similar memories
    search_query = f"{source_title} {source_content[:500]}"
    similar = await vector_store.similarity_search(
        query=search_query,
        limit=limit + 1,  # +1 to exclude self
        threshold=0.3
    )
    
    # Filter out the source memory and format results
    related = []
    for item in similar:
        if str(item.get("id")) != memory_id:
            related.append(RelatedMemory(
                id=str(item.get("id", "")),
                title=item.get("title", "Untitled"),
                similarity=item.get("similarity", 0)
            ))
        if len(related) >= limit:
            break
    
    return related
