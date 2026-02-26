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


class RelatedScrap(BaseModel):
    """관련 스크랩 추천 항목."""

    id: str
    title: str
    similarity: float


class RelatedScrapsResponse(BaseModel):
    """관련 스크랩 응답."""

    source_id: str
    related: list[RelatedScrap]
