# backend/app/agents/tools/report_tools.py
"""리포트 생성 도구 모음 — 일일 다이제스트, 인사이트, 주간/월간 리포트 4종."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id
from app.config.database import get_supabase_client
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.scrap_repository import ScrapRepository
from app.services.digest_service import DigestService
from app.services.insight_service import InsightService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


@tool
async def generate_daily_digest(
    date: str | None = None,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """지정한 날짜의 일일 다이제스트(스크랩·다이어리·채팅 요약)를 생성한다.

    Args:
        date: 조회 날짜 ("YYYY-MM-DD" 형식). None이면 오늘 날짜 사용.

    Returns:
        date, summary, scraps, diaries, chats, insights 필드를 포함한 다이제스트 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # target_date 파싱
    target_date: datetime | None = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            logger.warning("generate_daily_digest: 날짜 형식 오류 date=%s, 오늘 날짜 사용", date)

    service = DigestService(
        scrap_repo=container.scrap_repo,
        diary_repo=container.diary_repo,
        socrates_repo=container.socrates_repo,
    )

    try:
        return await service.get_today_digest(
            user_id=UUID(user_id),
            target_date=target_date,
        )
    except Exception:
        logger.exception("generate_daily_digest 오류: user_id=%s, date=%s", user_id, date)
        return {
            "date": date or datetime.now(UTC).date().isoformat(),
            "summary": {"scrap_count": 0, "diary_count": 0, "chat_count": 0},
            "scraps": [],
            "diaries": [],
            "chats": [],
            "insights": {"main_topics": [], "suggested_questions": ["오늘 하루는 어떠셨나요?"]},
        }


@tool
async def generate_daily_insights(
    date: str | None = None,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """오늘의 규칙 기반 일일 인사이트 목록(최대 3개)을 생성한다.

    Args:
        date: 현재 미사용 (InsightService는 오늘 기준 동작). 향후 확장용 파라미터.

    Returns:
        type, icon, title, description, cta_label, cta_path 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    db = get_supabase_client()
    calendar_repo = CalendarRepository(db)

    service = InsightService(
        calendar_repo=calendar_repo,
        mindmap_repo=container.mindmap_repo,
        diary_repo=container.diary_repo,
    )

    try:
        response = await service.get_daily_insights(user_id=user_id)
        return [insight.model_dump() for insight in response.insights]
    except Exception:
        logger.exception("generate_daily_insights 오류: user_id=%s", user_id)
        return []


@tool
async def generate_weekly_report(
    week_offset: int = 0,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """최근 7일(또는 week_offset 기준) 주간 리포트를 생성한다.

    Args:
        week_offset: 0이면 이번 주, -1이면 지난 주 (현재 ReportService는 0 기준 최근 7일 사용).

    Returns:
        period, date_range, total_scraps, total_diaries, topic_distribution,
        source_distribution, llm_summary, highlights 필드를 가진 dict
    """
    user_id = get_user_id(config)

    db = get_supabase_client()
    calendar_repo = CalendarRepository(db)
    scrap_repo = ScrapRepository(db)

    service = ReportService(
        calendar_repo=calendar_repo,
        scrap_repo=scrap_repo,
    )

    try:
        result = await service.get_weekly_report(user_id=UUID(user_id))
        return result.model_dump()
    except Exception:
        logger.exception("generate_weekly_report 오류: user_id=%s, week_offset=%s", user_id, week_offset)
        return {
            "period": "weekly",
            "date_range": "",
            "total_scraps": 0,
            "total_diaries": 0,
            "topic_distribution": [],
            "source_distribution": [],
            "llm_summary": "이번 주 활동",
            "highlights": [],
        }


@tool
async def generate_monthly_report(
    month_offset: int = 0,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """최근 30일(또는 month_offset 기준) 월간 리포트를 생성한다.

    Args:
        month_offset: 0이면 이번 달, -1이면 지난 달 (현재 ReportService는 0 기준 최근 30일 사용).

    Returns:
        period, date_range, total_scraps, total_diaries, topic_distribution,
        source_distribution, llm_summary, highlights 필드를 가진 dict
    """
    user_id = get_user_id(config)

    db = get_supabase_client()
    calendar_repo = CalendarRepository(db)
    scrap_repo = ScrapRepository(db)

    service = ReportService(
        calendar_repo=calendar_repo,
        scrap_repo=scrap_repo,
    )

    try:
        result = await service.get_monthly_report(user_id=UUID(user_id))
        return result.model_dump()
    except Exception:
        logger.exception("generate_monthly_report 오류: user_id=%s, month_offset=%s", user_id, month_offset)
        return {
            "period": "monthly",
            "date_range": "",
            "total_scraps": 0,
            "total_diaries": 0,
            "topic_distribution": [],
            "source_distribution": [],
            "llm_summary": "이번 달 활동",
            "highlights": [],
        }
