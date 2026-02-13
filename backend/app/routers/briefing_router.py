from uuid import UUID

from fastapi import APIRouter, Depends

from app.config.auth import get_user_id
from app.config.dependencies import get_digest_service, get_stats_service
from app.schemas.briefing_schema import (
    BriefingResponse,
    BriefingStreak,
    BriefingTodayMemories,
)
from app.services.digest_service import DigestService
from app.services.stats_service import StatsService

router = APIRouter(prefix="/briefing", tags=["briefing"])

MAX_TOPICS = 3


@router.get("/today", response_model=BriefingResponse)
async def get_today_briefing(
    user_id: UUID = Depends(get_user_id),
    digest_service: DigestService = Depends(get_digest_service),
    stats_service: StatsService = Depends(get_stats_service),
):
    """오늘의 브리핑 통합 조회. 다이제스트 + 스트릭 데이터를 경량 포맷으로 결합."""
    digest = await digest_service.get_today_digest(user_id=user_id)
    streak_data = await stats_service.get_streak(user_id)

    memory_count = digest["summary"]["memory_count"]
    journal_count = digest["summary"]["journal_count"]
    topics = digest["insights"]["main_topics"][:MAX_TOPICS]
    questions = digest["insights"]["suggested_questions"]

    # 회고하지 않은 메모리 수: 오늘 메모리 - 오늘 저널 수 (간략 추정)
    unreviewed = max(0, memory_count - journal_count)

    suggested_q = questions[0] if questions else "오늘 하루는 어떠셨나요?"

    return BriefingResponse(
        today_memories=BriefingTodayMemories(count=memory_count, topics=topics),
        unreviewed_count=unreviewed,
        streak=BriefingStreak(
            current=streak_data.current_streak,
            longest=streak_data.longest_streak,
        ),
        suggested_question=suggested_q,
        connection_hint=None,
    )
