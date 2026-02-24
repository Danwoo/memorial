import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.agents.librarian.graph import librarian_graph
from app.agents.state import build_librarian_initial_state
from app.config.auth import get_user_id
from app.config.dependencies import get_journal_service, get_memory_service
from app.schemas.journal_schema import (
    GenerateDraftRequest,
    GenerateDraftResponse,
    InsightsResponse,
    JournalCreate,
    JournalDateInfo,
    JournalDatesResponse,
    RelatedMemoriesResponse,
    RelatedMemoryItem,
    ReviewQuestionsResponse,
    ReviewRequest,
)
from app.services.journal_service import JournalService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/journals", tags=["journals"])


async def _process_journal_with_librarian(
    journal_id: str,
    content: str,
    user_id: str,
    memory_service: MemoryService,
) -> None:
    """백그라운드: 저널 내용을 메모리로 저장 후 Librarian 엔티티 추출."""
    try:
        memory = await memory_service.create_memory(
            user_id=UUID(user_id),
            title=f"저널 {journal_id[:8]}",
            content=content[:6000],
            source_type="JOURNAL",
        )
        if not memory:
            logger.warning("Failed to create memory for journal %s", journal_id)
            return

        memory_id = str(memory.id)

        initial_state = build_librarian_initial_state(memory_id, content[:6000], user_id)
        result = await librarian_graph.ainvoke(initial_state)
        logger.info(
            "Librarian processed journal %s: classification=%s",
            journal_id,
            result.get("classification"),
        )
    except Exception:
        logger.exception("Librarian error for journal %s", journal_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_journal(
    journal: JournalCreate,
    background_tasks: BackgroundTasks,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """새 저널 항목 생성 (감정 분석 + 엔티티 추출)."""
    try:
        result = await service.create_entry(user_id, journal.content, journal.memory_ids)
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create journal entry - no result returned",
            )

        # 충분한 길이의 저널은 Librarian으로 엔티티 추출
        if len(journal.content.strip()) >= 50:
            journal_id = result.get("id") or result.get("journal_id", "")
            background_tasks.add_task(
                _process_journal_with_librarian,
                str(journal_id),
                journal.content,
                str(user_id),
                memory_service,
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
    """현재 사용자의 저널 항목 목록 조회."""
    return await service.get_entries(user_id, limit)


@router.get("/dates", response_model=JournalDatesResponse)
async def get_journal_dates(
    limit: int = 90,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """저널이 존재하는 날짜 목록 조회."""
    dates = await service.get_journal_dates(user_id, limit)
    return JournalDatesResponse(dates=[JournalDateInfo(**d) for d in dates])


@router.get("/by-date/{date}")
async def get_journals_by_date(
    date: str,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """특정 날짜(YYYY-MM-DD)의 저널 목록 조회."""
    return await service.get_journals_by_date(user_id, date)


@router.post("/review-questions", response_model=ReviewQuestionsResponse)
async def get_review_questions(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """저널 내용 기반 소크라테스식 성찰 질문 생성."""
    try:
        questions = await service.generate_review_questions(request.content)
        return ReviewQuestionsResponse(questions=questions)
    except Exception:
        logger.exception("Failed to generate review questions")
        return ReviewQuestionsResponse(questions=["이 경험에서 어떤 인사이트를 얻었나요?"])


@router.post("/insights", response_model=InsightsResponse)
async def analyze_insights(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """저널 내용의 인지 왜곡 분석 및 피드백 제공."""
    try:
        insights = service.detect_cognitive_distortions(request.content)
        return InsightsResponse(**insights)
    except Exception:
        logger.exception("Failed to analyze cognitive distortions")
        return InsightsResponse(has_distortions=False, distortions=[], wellness_score=100)


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(
    request: GenerateDraftRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """저녁 대화 세션에서 저널 초안 생성."""
    try:
        draft = await service.generate_draft_from_conversation(request.session_id)
        return GenerateDraftResponse(draft=draft, session_id=request.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Failed to generate journal draft")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate journal draft",
        ) from None


@router.post("/related-memories", response_model=RelatedMemoriesResponse)
async def get_related_memories(
    request: ReviewRequest,
    user_id: UUID = Depends(get_user_id),
    service: JournalService = Depends(get_journal_service),
):
    """저널 내용과 관련된 메모리를 벡터 검색으로 조회."""
    try:
        results = await service.get_related_memories(user_id, request.content)
        memories = [RelatedMemoryItem(**m) for m in results]
        return RelatedMemoriesResponse(memories=memories)
    except Exception:
        logger.exception("Failed to fetch related memories")
        return RelatedMemoriesResponse(memories=[])
