# backend/app/agents/tools/retrieval_tools.py
"""스크랩/그래프 검색 도구 모음 — ReAct 에이전트용 retrieval tool 3종."""

from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id


@tool
async def search_scraps(
    query: str,
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """사용자 스크랩을 하이브리드 검색(Dense + Sparse + Graph)으로 조회한다.

    Args:
        query: 검색 쿼리 문자열
        limit: 최대 반환 결과 수 (기본 10)

    Returns:
        id, title, content_preview, tags, source_type, created_at, score 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    results = await container.hybrid_search.search(
        user_id=UUID(user_id),
        query=query,
        limit=limit,
    )

    output: list[dict[str, Any]] = []
    for r in results:
        content = r.get("content") or ""
        output.append(
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "content_preview": content[:300],
                "tags": r.get("tags") or [],
                "source_type": r.get("source_type", ""),
                "created_at": r.get("created_at", ""),
                "score": r.get("hybrid_score", 0.0),
            }
        )
    return output


@tool
async def search_graph_entities(
    keyword: str,
    entity_type: str = "",
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """Knowledge Graph에서 키워드로 엔티티를 검색한다.

    Args:
        keyword: 엔티티 이름 검색 키워드
        entity_type: 필터링할 엔티티 타입 (예: "Person", "Concept"). 빈 문자열이면 전체 타입
        limit: 최대 반환 결과 수 (기본 10)

    Returns:
        name, type 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    results = await container.mindmap_repo.search_entities(
        keyword=keyword,
        user_id=user_id,
        entity_type=entity_type,
        limit=limit,
    )
    return results


@tool
async def get_graph_context(
    topic: str,
    depth: int = 2,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Knowledge Graph에서 주제 엔티티와 연결된 관련 엔티티 컨텍스트를 조회한다.

    Args:
        topic: 탐색 중심 엔티티 이름
        depth: 탐색 깊이 (기본 2)

    Returns:
        topic, related_entities(name, type, rel_type, distance) 필드를 가진 dict
    """
    get_user_id(config)  # user_id 유효성 검증
    container = get_agent_container()

    related = await container.mindmap_repo.get_related_context(
        topic=topic,
        depth=depth,
    )

    return {
        "topic": topic,
        "related_entities": related,
    }
