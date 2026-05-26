import logging
import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.config.auth import get_user_id
from app.config.dependencies import (
    get_chat_service,
    get_diary_analysis_service,
    get_diary_orchestrator,
    get_diary_service,
)
from app.domain.diary import DiaryEntry
from app.orchestrators.diary_orchestrator import (
    MIN_DIARY_LENGTH_FOR_EXTRACTION,
    DiaryOrchestrator,
)
from app.schemas.diary_schema import (
    DiaryCreate,
    DiaryDateInfo,
    DiaryDatesResponse,
    DiaryUpdate,
    GenerateDraftRequest,
    GenerateDraftResponse,
    InsightsResponse,
    RelatedScrapItem,
    RelatedScrapsResponse,
    ReviewQuestionsResponse,
    ReviewRequest,
)
from app.services.chat_service import ChatService
from app.services.diary_analysis_service import DiaryAnalysisService
from app.services.diary_service import DiaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diaries", tags=["diaries"])


def _diary_to_dict(d: DiaryEntry) -> dict[str, Any]:
    """DiaryEntry 도메인 모델을 API 응답용 dict로 변환.

    프론트엔드 호환성을 위해 기존 JSON 키 유지.
    """
    return {
        "id": str(d.id),
        "user_id": str(d.user_id),
        "content": d.content,
        "mood": d.mood,
        "tags": d.tags,
        "created_at": d.created_at.isoformat() if d.created_at else "",
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_diary(
    diary: DiaryCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
    diary_orchestrator: DiaryOrchestrator = Depends(get_diary_orchestrator),
):
    """새 다이어리 항목 생성 (감정 분석 + 엔티티 추출)."""
    try:
        result = await diary_service.create_entry(user_id, diary.content, diary.scrap_ids)
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create diary entry - no result returned",
            )

        # 충분한 길이의 다이어리는 cross-domain orchestrator에 위임 (scrap 적재 + librarian 엔티티 추출)
        if len(diary.content.strip()) >= MIN_DIARY_LENGTH_FOR_EXTRACTION:
            background_tasks.add_task(
                diary_orchestrator.process_diary_with_librarian,
                str(result.id),
                diary.content,
                str(user_id),
            )

        return _diary_to_dict(result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create diary entry")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating diary entry",
        ) from None


@router.put("/{diary_id}")
async def update_diary(
    diary_id: UUID,
    body: DiaryUpdate,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """기존 다이어리 항목 수정."""
    try:
        result = await diary_service.update_entry(diary_id, user_id, body.content, body.scrap_ids)
        if not result:
            raise HTTPException(status_code=404, detail="Diary entry not found")
        return _diary_to_dict(result)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update diary entry %s", diary_id)
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get("/search")
async def search_diaries(
    q: str = Query(max_length=200),
    limit: int = Query(20, ge=1, le=100),
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """다이어리 내용 검색."""
    try:
        entries = await diary_service.get_entries(user_id, limit=limit)
        q_lower = q.lower()
        results = [e for e in entries if q_lower in (e.content or "").lower()]
        return [_diary_to_dict(e) for e in results[:limit]]
    except Exception:
        logger.exception("Failed to search diaries")
        raise HTTPException(status_code=500, detail="Search failed") from None


@router.get("")
async def list_diaries(
    limit: int = 10,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """현재 사용자의 다이어리 항목 목록 조회."""
    entries = await diary_service.get_entries(user_id, limit)
    return [_diary_to_dict(e) for e in entries]


@router.get("/dates", response_model=DiaryDatesResponse)
async def get_diary_dates(
    limit: int = 90,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """다이어리가 존재하는 날짜 목록 조회."""
    dates = await diary_service.get_diary_dates(user_id, limit)
    return DiaryDatesResponse(dates=[DiaryDateInfo(**d) for d in dates])


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("/by-date/{date}")
async def get_diaries_by_date(
    date: str,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """특정 날짜(YYYY-MM-DD)의 다이어리 목록 조회."""
    if not _DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")
    entries = await diary_service.get_diaries_by_date(user_id, date)
    return [_diary_to_dict(e) for e in entries]


@router.post("/review-questions", response_model=ReviewQuestionsResponse)
async def get_review_questions(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    analysis_service: DiaryAnalysisService = Depends(get_diary_analysis_service),
):
    """다이어리 내용 기반 소크라테스식 성찰 질문 생성."""
    try:
        questions = await analysis_service.generate_review_questions(request.content)
        return ReviewQuestionsResponse(questions=questions)
    except Exception:
        logger.exception("Failed to generate review questions")
        return ReviewQuestionsResponse(questions=["이 경험에서 어떤 인사이트를 얻었나요?"])


@router.post("/insights", response_model=InsightsResponse)
async def analyze_insights(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    analysis_service: DiaryAnalysisService = Depends(get_diary_analysis_service),
):
    """다이어리 내용의 인지 왜곡 분석 및 피드백 제공."""
    try:
        insights = await analysis_service.detect_cognitive_distortions(request.content)
        return InsightsResponse(**insights)
    except Exception:
        logger.exception("Failed to analyze cognitive distortions")
        return InsightsResponse(has_distortions=False, distortions=[], wellness_score=100)


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(
    request: GenerateDraftRequest,
    user_id: UUID = Depends(get_user_id),
    analysis_service: DiaryAnalysisService = Depends(get_diary_analysis_service),
    chat_service: ChatService = Depends(get_chat_service),
):
    """저녁 대화 세션에서 다이어리 초안 생성."""
    # 세션 소유권 검증 (IDOR 방어)
    session = await chat_service.get_session(request.session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        draft = await analysis_service.generate_draft_from_conversation(request.session_id)
        return GenerateDraftResponse(draft=draft, session_id=request.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Failed to generate diary draft")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate diary draft",
        ) from None


@router.post("/related-scraps", response_model=RelatedScrapsResponse)
async def get_related_scraps(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    analysis_service: DiaryAnalysisService = Depends(get_diary_analysis_service),
):
    """다이어리 내용과 관련된 스크랩을 벡터 검색으로 조회."""
    try:
        results = await analysis_service.get_related_scraps(user_id, request.content)
        scraps = [RelatedScrapItem(**m) for m in results]
        return RelatedScrapsResponse(scraps=scraps)
    except Exception:
        logger.exception("Failed to fetch related scraps")
        return RelatedScrapsResponse(scraps=[])
