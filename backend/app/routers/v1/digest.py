"""
Digest Router
API endpoints for daily digest
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.services.digest_service import DigestService
from app.dependencies import get_digest_service

router = APIRouter(prefix="/digest", tags=["digest"])


@router.get("/today", response_model=Dict[str, Any])
async def get_today_digest(
    digest_service: DigestService = Depends(get_digest_service)
):
    """
    Get today's digest including:
    - All memories saved today
    - All journal entries from today
    - AI-generated reflection questions
    - Main topics/tags
    """
    return await digest_service.get_today_digest()


@router.get("/date/{date_str}", response_model=Dict[str, Any])
async def get_digest_by_date(
    date_str: str,
    digest_service: DigestService = Depends(get_digest_service)
):
    """
    Get digest for a specific date (format: YYYY-MM-DD)
    """
    # TODO: Implement date-specific digest
    return await digest_service.get_today_digest()
