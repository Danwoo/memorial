import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.agents.librarian.graph import librarian_graph
from app.agents.state import build_librarian_initial_state
from app.config.auth import get_user_id
from app.config.dependencies import get_diary_analysis_service, get_diary_service, get_scrap_service
from app.schemas.diary_schema import (
    DiaryCreate,
    DiaryDateInfo,
    DiaryDatesResponse,
    GenerateDraftRequest,
    GenerateDraftResponse,
    InsightsResponse,
    RelatedScrapItem,
    RelatedScrapsResponse,
    ReviewQuestionsResponse,
    ReviewRequest,
)
from app.services.diary_analysis_service import DiaryAnalysisService
from app.services.diary_service import DiaryService
from app.services.scrap_service import ScrapService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diaries", tags=["diaries"])


async def _process_diary_with_librarian(
    diary_id: str,
    content: str,
    user_id: str,
    scrap_service: ScrapService,
) -> None:
    """백그라운드: 다이어리 내용을 스크랩으로 저장 후 Librarian 엔티티 추출."""
    try:
        scrap = await scrap_service.create_scrap(
            user_id=UUID(user_id),
            title=f"다이어리 {diary_id[:8]}",
            content=content[:6000],
            source_type="DIARY",
        )
        if not scrap:
            logger.warning("Failed to create scrap for diary %s", diary_id)
            return

        scrap_id = str(scrap.id)

        initial_state = build_librarian_initial_state(scrap_id, content[:6000], user_id)
        result = await librarian_graph.ainvoke(initial_state)
        logger.info(
            "Librarian processed diary %s: classification=%s",
            diary_id,
            result.get("classification"),
        )
    except Exception:
        logger.exception("Librarian error for diary %s", diary_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_diary(
    diary: DiaryCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
    scrap_service: ScrapService = Depends(get_scrap_service),
):
    """새 다이어리 항목 생성 (감정 분석 + 엔티티 추출)."""
    try:
        result = await diary_service.create_entry(user_id, diary.content, diary.scrap_ids)
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create diary entry - no result returned",
            )

        # 충분한 길이의 다이어리는 Librarian으로 엔티티 추출
        if len(diary.content.strip()) >= 50:
            diary_id = result.get("id") or result.get("diary_id", "")
            background_tasks.add_task(
                _process_diary_with_librarian,
                str(diary_id),
                diary.content,
                str(user_id),
                scrap_service,
            )

        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create diary entry")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating diary entry",
        ) from None


@router.get("")
async def list_diaries(
    limit: int = 10,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """현재 사용자의 다이어리 항목 목록 조회."""
    return await diary_service.get_entries(user_id, limit)


@router.get("/dates", response_model=DiaryDatesResponse)
async def get_diary_dates(
    limit: int = 90,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """다이어리가 존재하는 날짜 목록 조회."""
    dates = await diary_service.get_diary_dates(user_id, limit)
    return DiaryDatesResponse(dates=[DiaryDateInfo(**d) for d in dates])


@router.get("/by-date/{date}")
async def get_diaries_by_date(
    date: str,
    user_id: UUID = Depends(get_user_id),
    diary_service: DiaryService = Depends(get_diary_service),
):
    """특정 날짜(YYYY-MM-DD)의 다이어리 목록 조회."""
    return await diary_service.get_diaries_by_date(user_id, date)


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
        insights = analysis_service.detect_cognitive_distortions(request.content)
        return InsightsResponse(**insights)
    except Exception:
        logger.exception("Failed to analyze cognitive distortions")
        return InsightsResponse(has_distortions=False, distortions=[], wellness_score=100)


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(
    request: GenerateDraftRequest,
    user_id: UUID = Depends(get_user_id),
    analysis_service: DiaryAnalysisService = Depends(get_diary_analysis_service),
):
    """저녁 대화 세션에서 다이어리 초안 생성."""
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
