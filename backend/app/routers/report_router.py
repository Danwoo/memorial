from uuid import UUID

from fastapi import APIRouter, Depends

from app.config.auth import get_user_id
from app.config.dependencies import get_report_service
from app.schemas.report_schema import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly", response_model=ReportResponse)
async def get_weekly_report(
    user_id: UUID = Depends(get_user_id),
    service: ReportService = Depends(get_report_service),
):
    """주간 AI 리포트."""
    return await service.get_weekly_report(user_id)


@router.get("/monthly", response_model=ReportResponse)
async def get_monthly_report(
    user_id: UUID = Depends(get_user_id),
    service: ReportService = Depends(get_report_service),
):
    """월간 AI 리포트."""
    return await service.get_monthly_report(user_id)
