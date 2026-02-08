"""
Journal Router
API endpoints for journal operations
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.config.auth import get_user_id
from app.config.dependencies import get_journal_service
from app.schemas.journal_schema import (
    InsightsResponse,
    JournalCreate,
    RelatedMemoriesResponse,
    RelatedMemoryItem,
    ReviewQuestionsResponse,
    ReviewRequest,
)
from app.services.journal_service import JournalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journals", tags=["journals"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_journal(
    journal: JournalCreate,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """Create a new journal entry with mood analysis."""
    try:
        result = await service.create_entry(user_id, journal.content)
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create journal entry - no result returned",
            )
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create journal entry")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating journal entry",
        ) from None


@router.get("")
async def list_journals(
    limit: int = 10,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """List journal entries for the current user."""
    return await service.get_entries(user_id, limit)


@router.post("/review-questions", response_model=ReviewQuestionsResponse)
async def get_review_questions(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """Generate Socratic review questions based on journal content."""
    try:
        questions = service.generate_review_questions(request.content)
        return ReviewQuestionsResponse(questions=questions)
    except Exception:
        logger.exception("Failed to generate review questions")
        return ReviewQuestionsResponse(
            questions=["이 경험에서 어떤 인사이트를 얻었나요?"]
        )


@router.post("/insights", response_model=InsightsResponse)
async def analyze_insights(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """Analyze journal content for cognitive distortions and provide feedback."""
    try:
        insights = service.detect_cognitive_distortions(request.content)
        return InsightsResponse(**insights)
    except Exception:
        logger.exception("Failed to analyze cognitive distortions")
        return InsightsResponse(
            has_distortions=False, distortions=[], wellness_score=100
        )


@router.post("/related-memories", response_model=RelatedMemoriesResponse)
async def get_related_memories(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """Find memories related to the current journal content for context sidebar."""
    try:
        results = await service.get_related_memories(user_id, request.content)
        memories = [RelatedMemoryItem(**m) for m in results]
        return RelatedMemoriesResponse(memories=memories)
    except Exception:
        logger.exception("Failed to fetch related memories")
        return RelatedMemoriesResponse(memories=[])
