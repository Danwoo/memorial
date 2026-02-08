"""
Journal Router
API endpoints for journal operations
"""
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.config.settings import DEFAULT_USER_ID
from app.dependencies import get_journal_service, get_vector_repository
from app.repositories.vector_repository import VectorRepository
from app.services.journal_service import JournalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journals", tags=["journals"])


class JournalCreate(BaseModel):
    content: str


class JournalResponse(BaseModel):
    id: UUID
    content: str
    mood: str | None
    created_at: str
    updated_at: str


class ReviewRequest(BaseModel):
    content: str


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_journal(
    journal: JournalCreate,
    service: JournalService = Depends(get_journal_service),
):
    try:
        # Dev mode: skip user_id (FK constraint)
        result = await service.create_entry(None, journal.content)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create journal entry - no result returned")
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create journal entry")
        raise HTTPException(status_code=500, detail="Internal server error while creating journal entry") from None


@router.get("", response_model=list[dict[str, Any]])
async def list_journals(
    limit: int = 10,
    service: JournalService = Depends(get_journal_service),
):
    user_id = DEFAULT_USER_ID
    return await service.get_entries(user_id, limit)


@router.post("/review-questions", response_model=dict[str, Any])
def get_review_questions(
    request: ReviewRequest,
    service: JournalService = Depends(get_journal_service),
):
    """Generate Socratic review questions based on journal content."""
    try:
        questions = service.generate_review_questions(request.content)
        return {"questions": questions}
    except Exception:
        logger.exception("Failed to generate review questions")
        return {"questions": ["이 경험에서 어떤 인사이트를 얻었나요?"]}


@router.post("/insights", response_model=dict[str, Any])
def analyze_insights(
    request: ReviewRequest,
    service: JournalService = Depends(get_journal_service),
):
    """Analyze journal content for cognitive distortions and provide feedback."""
    try:
        insights = service.detect_cognitive_distortions(request.content)
        return insights
    except Exception:
        logger.exception("Failed to analyze cognitive distortions")
        return {"has_distortions": False, "distortions": [], "wellness_score": 100}


@router.post("/related-memories", response_model=dict[str, Any])
async def get_related_memories(
    request: ReviewRequest,
    vector_repo: VectorRepository = Depends(get_vector_repository),
):
    """Find memories related to the current journal content for context sidebar."""
    try:
        if not request.content or len(request.content.strip()) < 10:
            return {"memories": []}

        results = await vector_repo.similarity_search(
            query=request.content,
            limit=5,
            threshold=0.4,
        )

        memories = [
            {
                "id": m.get("id"),
                "title": m.get("title", "Untitled"),
                "summary": m.get("summary") or m.get("content", "")[:100],
                "type": m.get("type", "memory"),
                "created_at": m.get("created_at"),
                "similarity": m.get("similarity", 0),
            }
            for m in results
        ]

        return {"memories": memories}
    except Exception:
        logger.exception("Failed to fetch related memories")
        return {"memories": []}
