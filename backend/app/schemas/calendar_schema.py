from pydantic import BaseModel


class CalendarOverview(BaseModel):
    """캘린더 전체 통계 요약."""

    total_scraps: int
    total_this_week: int
    total_this_month: int
    most_active_day: str | None = None


class ActivityData(BaseModel):
    """일별 활동 데이터."""

    date: str
    count: int


class SourceCalendarStats(BaseModel):
    """소스 유형별 통계."""

    source_type: str
    count: int
    percentage: float


class TagCalendarStats(BaseModel):
    """태그 사용 통계."""

    tag: str
    count: int


class CalendarOverviewResponse(BaseModel):
    """캘린더 통계 개요 응답."""

    overview: CalendarOverview
    recent_activity: list[ActivityData]
    sources: list[SourceCalendarStats]
    top_tags: list[TagCalendarStats]


class CalendarStreakResponse(BaseModel):
    """캘린더 활동 스트릭 응답."""

    current_streak: int
    longest_streak: int
    total_active_days: int
    last_active_date: str | None = None


class TimelineGroup(BaseModel):
    """날짜별 스크랩 그룹."""

    date: str
    scraps: list[dict]


class TimelineResponse(BaseModel):
    """페이지네이션된 타임라인 응답."""

    page: int
    limit: int
    timeline: list[TimelineGroup]
    has_more: bool
