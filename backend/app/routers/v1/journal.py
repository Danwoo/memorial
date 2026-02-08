from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from uuid import UUID

from app.services.journal_service import JournalService
from app.dependencies import get_journal_service

router = APIRouter(prefix="/journals", tags=["journals"])

class JournalCreate(BaseModel):
    content: str

class JournalResponse(BaseModel):
    id: UUID
    content: str
    mood: str | None
    created_at: str
    updated_at: str

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_journal(
    journal: JournalCreate,
    service: JournalService = Depends(get_journal_service),
):
    try:
        # Dev mode: skip user_id (FK constraint)
        result = service.create_entry(None, journal.content)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create journal entry - no result returned")
        return result
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"[JOURNAL ERROR] {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("", response_model=List[Dict[str, Any]])
def list_journals(
    limit: int = 10,
    service: JournalService = Depends(get_journal_service)
):
    user_id = UUID("00000000-0000-0000-0000-000000000001")
    return service.get_entries(user_id, limit)

class ReviewRequest(BaseModel):
    content: str

@router.post("/review-questions", response_model=Dict[str, Any])
def get_review_questions(
    request: ReviewRequest,
    service: JournalService = Depends(get_journal_service)
):
    """Generate Socratic review questions based on journal content."""
    try:
        questions = service.generate_review_questions(request.content)
        return {"questions": questions}
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[REVIEW ERROR] {error_detail}\n{traceback.format_exc()}")
        return {"questions": ["이 경험에서 어떤 인사이트를 얻었나요?"]}

@router.post("/insights", response_model=Dict[str, Any])
def analyze_insights(
    request: ReviewRequest,
    service: JournalService = Depends(get_journal_service)
):
    """Analyze journal content for cognitive distortions and provide feedback."""
    try:
        insights = service.detect_cognitive_distortions(request.content)
        return insights
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[INSIGHT ERROR] {error_detail}\n{traceback.format_exc()}")
        return {"has_distortions": False, "distortions": [], "wellness_score": 100}

@router.post("/related-memories", response_model=Dict[str, Any])
async def get_related_memories(
    request: ReviewRequest,
):
    """Find memories related to the current journal content for context sidebar."""
    from app.infrastructure.database import get_supabase_client
    from app.repositories.vector_repository import VectorRepository

    vector_repo = VectorRepository(get_supabase_client())
    try:
        # Search for similar memories based on journal content
        if not request.content or len(request.content.strip()) < 10:
            return {"memories": []}

        results = await vector_repo.similarity_search(
            query=request.content,
            limit=5,
            threshold=0.4
        )
        
        # Format results for frontend
        memories = [
            {
                "id": m.get("id"),
                "title": m.get("title", "Untitled"),
                "summary": m.get("summary") or m.get("content", "")[:100],
                "type": m.get("type", "memory"),
                "created_at": m.get("created_at"),
                "similarity": m.get("similarity", 0)
            }
            for m in results
        ]
        
        return {"memories": memories}
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        print(f"[RELATED ERROR] {error_detail}\n{traceback.format_exc()}")
        return {"memories": []}
