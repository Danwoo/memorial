"""
Digest Router
API endpoints for daily digest
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config.auth import get_user_id
from app.config.dependencies import get_digest_service
from app.schemas.digest_schema import DigestResponse
from app.services.digest_service import DigestService

router = APIRouter(prefix="/digest", tags=["digest"])


@router.get("/today", response_model=DigestResponse)
async def get_today_digest(
    user_id: UUID = Depends(get_user_id),
    digest_service: DigestService = Depends(get_digest_service),
):
    """
    Get today's digest including:
    - All memories saved today
    - All journal entries from today
    - AI-generated reflection questions
    - Main topics/tags
    """
    return await digest_service.get_today_digest(user_id=user_id)


@router.get("/date/{date_str}", response_model=DigestResponse)
async def get_digest_by_date(
    date_str: str,
    user_id: UUID = Depends(get_user_id),
    digest_service: DigestService = Depends(get_digest_service),
):
    """Get digest for a specific date (format: YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD") from None
    return await digest_service.get_today_digest(user_id=user_id, target_date=target_date)
