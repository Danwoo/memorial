# backend/app/agents/tools/stats_tools.py
"""통계 및 활동 분석 도구 모음 — 지식 베이스 현황, 태그 분포, 활동 스트릭."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id


@tool
async def get_knowledge_stats(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자의 지식 베이스 전체 통계를 반환한다.

    Returns:
        total_scraps, total_diaries, total_sessions, total_entities,
        total_relations 필드를 가진 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 스크랩 수
    _, total_scraps = await container.scrap_repo.get_by_user(
        user_id=UUID(user_id),
        page=1,
        limit=1,
    )

    # 다이어리 통계
    diary_stats = await container.diary_repo.get_diary_statistics(user_id=user_id)
    total_diaries = diary_stats.get("total_count", 0)

    # 채팅 세션 수
    sessions = await container.chat_repo.get_sessions_by_user(user_id=UUID(user_id))
    total_sessions = len(sessions)

    # 그래프 엔티티/관계 수
    edges = await container.mindmap_repo.get_all_edges(user_id=user_id)
    total_relations = len(edges)
    entity_set: set[str] = set()
    for e in edges:
        if e.get("source"):
            entity_set.add(e["source"])
        if e.get("target"):
            entity_set.add(e["target"])
    total_entities = len(entity_set)

    return {
        "total_scraps": total_scraps,
        "total_diaries": total_diaries,
        "total_sessions": total_sessions,
        "total_entities": total_entities,
        "total_relations": total_relations,
    }


@tool
async def get_topic_distribution(
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """스크랩 태그 빈도 분포를 반환한다.

    Args:
        limit: 반환할 상위 태그 수 (기본 10)

    Returns:
        tag, count 필드를 가진 dict 리스트 (빈도 내림차순)
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 전체 스크랩의 raw tags 수집
    all_scraps = await container.scrap_repo.get_all(
        user_id=UUID(user_id),
        limit=5000,
    )

    tag_counts: dict[str, int] = {}
    for scrap in all_scraps:
        tags = scrap.get("tags") or []
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"tag": tag, "count": count} for tag, count in sorted_tags[:limit]]


@tool
async def get_activity_streak(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자의 다이어리 작성 활동 스트릭을 계산하여 반환한다.

    Returns:
        current_streak(현재 연속 작성일), longest_streak(최장 연속 작성일),
        total_active_days(전체 활동일 수), last_active_date(마지막 활동 날짜) 필드를 가진 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 최근 365일의 날짜 목록 조회
    dates_raw = await container.diary_repo.list_diary_dates(user_id=user_id, limit=365)

    if not dates_raw:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_active_days": 0,
            "last_active_date": "",
        }

    # 날짜 문자열을 date 객체로 변환 후 중복 제거 및 정렬
    date_set: set[str] = set()
    for d in dates_raw:
        if d and len(d) >= 10:
            date_set.add(d[:10])

    sorted_dates = sorted(date_set, reverse=True)
    total_active_days = len(sorted_dates)
    last_active_date = sorted_dates[0] if sorted_dates else ""

    # 현재 연속 스트릭 계산
    current_streak = 0
    today = datetime.now(UTC).date()
    check_date = today

    for date_str in sorted_dates:
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if entry_date == check_date or entry_date == check_date - timedelta(days=1):
            current_streak += 1
            check_date = entry_date - timedelta(days=1)
        elif entry_date < check_date - timedelta(days=1):
            break

    # 최장 연속 스트릭 계산
    longest_streak = 0
    current_run = 1
    for i in range(len(sorted_dates) - 1):
        d1 = datetime.strptime(sorted_dates[i], "%Y-%m-%d").date()
        d2 = datetime.strptime(sorted_dates[i + 1], "%Y-%m-%d").date()
        if d1 - d2 == timedelta(days=1):
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 1
    longest_streak = max(longest_streak, current_run if sorted_dates else 0)

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_active_days": total_active_days,
        "last_active_date": last_active_date,
    }
