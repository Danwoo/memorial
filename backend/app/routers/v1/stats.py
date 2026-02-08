"""
Stats Router
API endpoints for dashboard statistics
"""
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_stats_service
from app.schemas.stats import StatsOverviewResponse
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverviewResponse)
async def get_overview_stats(
    stats_service: StatsService = Depends(get_stats_service)
):
    """Get complete dashboard statistics overview."""
    return await stats_service.get_overview()


@router.get("/activity")
async def get_activity_data(
    days: int = Query(30, ge=1, le=365),
    stats_service: StatsService = Depends(get_stats_service)
):
    """Get daily activity data for a range."""
    activity = await stats_service.get_activity(days)
    return {"days": days, "activity": activity}


@router.get("/timeline")
async def get_timeline_data(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    stats_service: StatsService = Depends(get_stats_service)
):
    """Get memories grouped by date for timeline view."""
    return await stats_service.get_timeline(page, limit)
