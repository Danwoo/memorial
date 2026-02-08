"""
Stats Schemas
Request/Response DTOs for statistics/dashboard endpoints
"""
from pydantic import BaseModel
from typing import Optional, List


class OverviewStats(BaseModel):
    """Overview statistics summary"""
    total_memories: int
    total_this_week: int
    total_this_month: int
    most_active_day: Optional[str] = None


class ActivityData(BaseModel):
    """Daily activity data point"""
    date: str
    count: int


class SourceStats(BaseModel):
    """Statistics by source type"""
    source_type: str
    count: int
    percentage: float


class TagStats(BaseModel):
    """Tag usage statistics"""
    tag: str
    count: int


class StatsOverviewResponse(BaseModel):
    """Complete stats overview for dashboard"""
    overview: OverviewStats
    recent_activity: List[ActivityData]
    sources: List[SourceStats]
    top_tags: List[TagStats]


class TimelineGroup(BaseModel):
    """Memories grouped by date"""
    date: str
    memories: List[dict]


class TimelineResponse(BaseModel):
    """Paginated timeline response"""
    page: int
    limit: int
    timeline: List[TimelineGroup]
    has_more: bool
