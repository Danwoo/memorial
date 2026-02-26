from uuid import UUID

from pydantic import BaseModel


class DuplicatePairItem(BaseModel):
    """중복 쌍의 개별 스크랩 요약."""

    id: UUID
    title: str
    summary: str | None = None
    source_type: str
    source_url: str | None = None
    tags: list[str] | None = None


class DuplicatePair(BaseModel):
    """중복 스크랩 쌍."""

    scrap_a: DuplicatePairItem
    scrap_b: DuplicatePairItem
    similarity: float
    reason: str


class DuplicatesResponse(BaseModel):
    """중복 감지 결과."""

    pairs: list[DuplicatePair]
    total: int


class MergeRequest(BaseModel):
    """병합 요청."""

    keep_id: UUID
    merge_id: UUID


class MergeResponse(BaseModel):
    """병합 결과."""

    kept_id: UUID
    merged_tags: list[str]
