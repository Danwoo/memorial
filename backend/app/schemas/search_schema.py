"""
Search Schemas
Request/Response DTOs for search endpoints
"""

from pydantic import BaseModel


class SearchResult(BaseModel):
    """Single search result item"""

    id: str
    title: str
    content: str
    summary: str | None = None
    source_type: str
    similarity: float
    created_at: str | None = None
    tags: list[str] | None = None


class SearchResponse(BaseModel):
    """Search response with results and metadata"""

    query: str
    results: list[SearchResult]
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
    related: list[RelatedMemory]
