import asyncio
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config.auth import get_user_id
from app.config.dependencies import get_digest_service
from app.schemas.digest_schema import DigestResponse
from app.services.digest_service import DigestService
from app.services.scheduler_service import digest_delivery_job

router = APIRouter(prefix="/digest", tags=["digest"])


@router.get("/today", response_model=DigestResponse)
async def get_today_digest(
    user_id: UUID = Depends(get_user_id),
    digest_service: DigestService = Depends(get_digest_service),
):
    """오늘의 다이제스트 조회 (메모리, 저널, AI 성찰 질문, 주요 토픽 포함)."""
    return await digest_service.get_today_digest(user_id=user_id)


@router.get("/date/{date_str}", response_model=DigestResponse)
async def get_digest_by_date(
    date_str: str,
    user_id: UUID = Depends(get_user_id),
    digest_service: DigestService = Depends(get_digest_service),
):
    """특정 날짜의 다이제스트 조회 (형식: YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") from None
    return await digest_service.get_today_digest(user_id=user_id, target_date=target_date)


@router.post("/trigger-delivery")
async def trigger_digest_delivery(
    user_id: UUID = Depends(get_user_id),
):
    """다이제스트 배달 작업 수동 트리거 (관리용)."""
    asyncio.create_task(digest_delivery_job())
    return {"status": "triggered"}
