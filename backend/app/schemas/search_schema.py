from pydantic import BaseModel


class SearchResult(BaseModel):
    """검색 결과 항목."""

    id: str
    title: str
    content: str
    summary: str | None = None
    source_type: str
    similarity: float
    created_at: str | None = None
    tags: list[str] | None = None


class SearchResponse(BaseModel):
    """검색 결과 및 메타데이터 응답."""

    query: str
    results: list[SearchResult]
    total: int
    filters_applied: dict


class RelatedMemory(BaseModel):
    """관련 메모리 추천 항목."""

    id: str
    title: str
    similarity: float


class RelatedMemoriesResponse(BaseModel):
    """관련 메모리 응답."""

    source_id: str
    related: list[RelatedMemory]
