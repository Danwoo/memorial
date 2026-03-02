# backend/app/agents/tools/session_tools.py
"""소크라테스 세션 관련 도구 모음 — 과거 대화 검색, 사용자 프로필 조회."""

from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id


@tool
async def search_past_conversations(
    query: str,
    limit: int = 3,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """과거 소크라테스 대화 세션을 토픽 태그 기반으로 검색한다.

    Args:
        query: 검색 쿼리 (공백 구분 키워드를 태그로 분리하여 검색)
        limit: 최대 반환 세션 수 (기본 3)

    Returns:
        session_id, title, summary_preview, created_at 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 쿼리를 키워드로 분리하여 topic_tags 검색에 활용
    tags = [kw.strip() for kw in query.split() if len(kw.strip()) >= 2]
    if not tags:
        tags = [query.strip()]

    sessions = await container.socrates_repo.search_sessions_by_topic(
        user_id=UUID(user_id),
        tags=tags,
        limit=limit,
    )

    if not sessions:
        # topic_tags 검색 결과가 없으면 최근 세션 fallback
        all_sessions = await container.socrates_repo.get_sessions_by_user(
            user_id=UUID(user_id),
        )
        sessions = all_sessions[:limit]

    results: list[dict[str, Any]] = []
    for s in sessions:
        summary = s.get("summary") or ""
        results.append(
            {
                "session_id": s.get("id", ""),
                "title": s.get("title", ""),
                "summary_preview": summary[:200],
                "created_at": s.get("created_at", ""),
            }
        )
    return results


@tool
async def get_user_profile(
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """사용자 관심사와 자주 등장하는 토픽을 분석하여 프로필을 반환한다.

    Returns:
        interests(스크랩 상위 태그), frequent_topics(그래프 허브 엔티티) 필드를 가진 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 스크랩의 고유 태그 목록 → 상위 관심사
    all_tags = await container.scrap_repo.get_distinct_tags(UUID(user_id))

    # 그래프 허브 엔티티 → 자주 등장하는 토픽
    hub_entities = await container.mindmap_repo.get_hub_entities(
        user_id=user_id,
        limit=10,
    )
    frequent_topics = [
        {"name": e.get("name", ""), "type": e.get("type", ""), "connection_count": e.get("connection_count", 0)}
        for e in hub_entities
    ]

    return {
        "interests": all_tags[:20],
        "frequent_topics": frequent_topics,
    }
