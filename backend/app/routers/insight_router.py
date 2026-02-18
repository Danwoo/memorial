from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config.auth import get_user_id
from app.config.dependencies import get_insight_service
from app.schemas.insight_schema import DailyInsightsResponse
from app.services.insight_service import InsightService

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/daily", response_model=DailyInsightsResponse)
async def get_daily_insights(
    user_id: UUID = Depends(get_user_id),
    insight_service: InsightService = Depends(get_insight_service),
):
    """일일 AI 인사이트 조회 (패턴/연결/행동 제안)."""
    try:
        return await insight_service.get_daily_insights(str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
