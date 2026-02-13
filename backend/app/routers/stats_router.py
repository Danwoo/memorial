from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.config.auth import get_user_id
from app.config.dependencies import get_stats_service
from app.schemas.stats_schema import StatsOverviewResponse, StreakResponse, TimelineResponse
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverviewResponse)
async def get_overview_stats(
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """대시보드 전체 통계 개요 조회."""
    return await stats_service.get_overview(user_id)


@router.get("/streak", response_model=StreakResponse)
async def get_streak(
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """활동 스트릭 (연속 활동일) 조회."""
    return await stats_service.get_streak(user_id)


@router.get("/activity")
async def get_activity_data(
    days: int = Query(30, ge=1, le=365),
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """지정 기간의 일별 활동 데이터 조회."""
    activity = await stats_service.get_activity(user_id, days)
    return {"days": days, "activity": activity}


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline_data(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_user_id),
    stats_service: StatsService = Depends(get_stats_service),
):
    """날짜별 메모리 그룹 타임라인 조회."""
    return await stats_service.get_timeline(user_id, page, limit)
