"""
Stats Router
API endpoints for dashboard statistics
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.config.auth import get_user_id
from app.config.dependencies import get_stats_service
from app.schemas.stats_schema import StatsOverviewResponse, TimelineResponse
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverviewResponse)
async def get_overview_stats(
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get complete dashboard statistics overview."""
    return await stats_service.get_overview(user_id)


@router.get("/activity")
async def get_activity_data(
    days: int = Query(30, ge=1, le=365),
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get daily activity data for a range."""
    activity = await stats_service.get_activity(user_id, days)
    return {"days": days, "activity": activity}


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline_data(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """Get memories grouped by date for timeline view."""
    return await stats_service.get_timeline(user_id, page, limit)
