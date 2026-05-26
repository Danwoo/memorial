# backend/app/agents/tools/diary_tools.py
"""일기 관련 tool 정의."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id


@tool
async def search_diaries(
    query: str,
    limit: int = 5,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """사용자 일기를 텍스트 쿼리로 검색한다.

    Args:
        query: 검색 키워드 (제목 또는 본문 내 포함 여부 확인)
        limit: 최대 반환 결과 수 (기본 5)

    Returns:
        id, title, content_preview, mood, tags, created_at 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    rows = await container.diary_repo.search_diaries(
        query=query,
        user_id=user_id,
        limit=limit,
    )

    output: list[dict[str, Any]] = []
    for r in rows:
        content = r.content or ""
        output.append(
            {
                "id": str(r.id),
                "title": "",
                "content_preview": content[:300],
                "mood": r.mood or "",
                "tags": r.tags or [],
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
        )
    return output


@tool
async def get_diary_detail(
    diary_id: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """특정 일기의 전체 내용을 조회한다.

    Args:
        diary_id: 조회할 일기의 UUID 문자열

    Returns:
        id, title, content, mood, tags, created_at, updated_at 필드를 가진 dict.
        해당 일기가 없으면 빈 dict 반환.
    """
    from uuid import UUID

    user_id = get_user_id(config)
    container = get_agent_container()

    row = await container.diary_repo.get_diary_by_id(
        diary_id=diary_id,
        user_id=UUID(user_id),
    )

    if not row:
        return {}

    return {
        "id": str(row.id),
        "title": "",
        "content": row.content or "",
        "mood": row.mood or "",
        "tags": row.tags or [],
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


@tool
async def get_emotion_trend(
    days: int = 7,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """최근 N일간 작성된 일기의 감정 추세를 반환한다.

    Args:
        days: 조회 기간 (일 단위, 기본 7일)

    Returns:
        id, title, mood, tags, created_at 필드를 가진 dict 리스트 (최신 순)
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    rows = await container.diary_repo.get_emotion_trend(
        user_id=user_id,
        days=days,
    )

    output: list[dict[str, Any]] = []
    for r in rows:
        output.append(
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "mood": r.get("mood", ""),
                "tags": r.get("tags") or [],
                "created_at": r.get("created_at", ""),
            }
        )
    return output


@tool
async def list_diary_dates(
    limit: int = 30,
    *,
    config: RunnableConfig,
) -> list[str]:
    """사용자가 일기를 작성한 날짜 목록을 반환한다.

    Args:
        limit: 최대 반환 날짜 수 (기본 30)

    Returns:
        YYYY-MM-DD 형식의 날짜 문자열 리스트 (최신 순)
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    return await container.diary_repo.list_diary_dates(
        user_id=user_id,
        limit=limit,
    )


@tool
async def get_diary_statistics(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자 일기 작성 통계를 반환한다.

    Returns:
        total_count(총 일기 수), mood_distribution(감정별 일기 수 dict) 필드를 가진 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    return await container.diary_repo.get_diary_statistics(user_id=user_id)
