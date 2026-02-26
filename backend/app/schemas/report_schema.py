from pydantic import BaseModel


class TopicDistribution(BaseModel):
    """주제별 분포 항목."""

    topic: str
    count: int
    percentage: float


class SourceDistribution(BaseModel):
    """소스 타입별 분포."""

    source_type: str
    count: int
    percentage: float


class ReportResponse(BaseModel):
    """AI 리포트 응답."""

    period: str
    date_range: str
    total_scraps: int
    total_diaries: int
    topic_distribution: list[TopicDistribution]
    source_distribution: list[SourceDistribution]
    llm_summary: str
    highlights: list[str]
