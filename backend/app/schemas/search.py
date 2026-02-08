"""
Search Schemas
Request/Response DTOs for search endpoints
"""
from pydantic import BaseModel
from typing import Optional, List


class SearchResult(BaseModel):
    """Single search result item"""
    id: str
    title: str
    content: str
    summary: Optional[str] = None
    source_type: str
    similarity: float
    created_at: Optional[str] = None
    tags: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search response with results and metadata"""
    query: str
    results: List[SearchResult]
    total: int
    filters_applied: dict


class RelatedMemory(BaseModel):
    """Related memory item for recommendations"""
    id: str
    title: str
    similarity: float


class RelatedMemoriesResponse(BaseModel):
    """Response for related memories endpoint"""
    source_id: str
    related: List[RelatedMemory]
