from pydantic import BaseModel


class OverviewStats(BaseModel):
    """전체 통계 요약."""

    total_memories: int
    total_this_week: int
    total_this_month: int
    most_active_day: str | None = None


class ActivityData(BaseModel):
    """일별 활동 데이터."""

    date: str
    count: int


class SourceStats(BaseModel):
    """소스 유형별 통계."""

    source_type: str
    count: int
    percentage: float


class TagStats(BaseModel):
    """태그 사용 통계."""

    tag: str
    count: int


class StatsOverviewResponse(BaseModel):
    """대시보드 통계 개요 응답."""

    overview: OverviewStats
    recent_activity: list[ActivityData]
    sources: list[SourceStats]
    top_tags: list[TagStats]


class TimelineGroup(BaseModel):
    """날짜별 메모리 그룹."""

    date: str
    memories: list[dict]


class TimelineResponse(BaseModel):
    """페이지네이션된 타임라인 응답."""

    page: int
    limit: int
    timeline: list[TimelineGroup]
    has_more: bool
