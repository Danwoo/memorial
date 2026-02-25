from uuid import UUID

from fastapi import APIRouter, Depends

from app.config.auth import get_user_id
from app.config.dependencies import get_calendar_service, get_digest_service
from app.schemas.briefing_schema import (
    BriefingResponse,
    BriefingStreak,
    BriefingTodayScraps,
)
from app.services.calendar_service import CalendarService
from app.services.digest_service import DigestService

router = APIRouter(prefix="/briefing", tags=["briefing"])

MAX_TOPICS = 3


@router.get("/today", response_model=BriefingResponse)
async def get_today_briefing(
    user_id: UUID = Depends(get_user_id),
    digest_service: DigestService = Depends(get_digest_service),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    """오늘의 브리핑 통합 조회. 다이제스트 + 스트릭 데이터를 경량 포맷으로 결합."""
    digest = await digest_service.get_today_digest(user_id=user_id)
    streak_data = await calendar_service.get_streak(user_id)

    scrap_count = digest["summary"]["scrap_count"]
    diary_count = digest["summary"]["diary_count"]
    topics = digest["insights"]["main_topics"][:MAX_TOPICS]
    questions = digest["insights"]["suggested_questions"]

    # 회고하지 않은 스크랩 수: 오늘 스크랩 - 오늘 다이어리 수 (간략 추정)
    unreviewed = max(0, scrap_count - diary_count)

    suggested_q = questions[0] if questions else "오늘 하루는 어떠셨나요?"

    return BriefingResponse(
        today_scraps=BriefingTodayScraps(count=scrap_count, topics=topics),
        unreviewed_count=unreviewed,
        streak=BriefingStreak(
            current=streak_data.current_streak,
            longest=streak_data.longest_streak,
        ),
        suggested_question=suggested_q,
        connection_hint=None,
    )
