# backend/app/agents/tools/delegation_tools.py
"""위임 도구 모음 — 에이전트 간 작업 위임 3종 (무한 루프 방지 depth 체크 포함)."""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.tools._context import get_user_id

logger = logging.getLogger(__name__)

# 위임 최대 깊이 상수.
# 참고: 각 도구는 서브 에이전트를 재귀 호출하는 대신 하위 도구(retrieval_tools 등)를
# 직접 ainvoke 하므로 delegation_depth는 실제로 증가하지 않는다.
# 무한 루프 방지는 LangGraph 자체의 recursion_limit(RunnableConfig)이 담당한다.
# 따라서 아래 depth 체크는 방어적 코드로만 남겨두며, 실제 동작에는 영향 없다.
_MAX_DELEGATION_DEPTH = 2


def _get_delegation_depth(config: RunnableConfig) -> int:
    """RunnableConfig에서 현재 위임 깊이를 반환한다."""
    return (config.get("configurable") or {}).get("delegation_depth", 0)


@tool
async def delegate_to_librarian(
    query: str,
    context: str = "",
    *,
    config: RunnableConfig,
) -> str:
    """Librarian 에이전트에게 스크랩/그래프 검색 작업을 위임한다.

    스크랩 하이브리드 검색과 그래프 엔티티 검색을 직접 수행하여
    결과를 텍스트 형식으로 반환한다.

    Args:
        query: 검색 쿼리 문자열
        context: 추가 컨텍스트 (선택 사항)

    Returns:
        검색 결과를 요약한 텍스트 문자열
    """
    depth = _get_delegation_depth(config)
    if depth >= _MAX_DELEGATION_DEPTH:
        return f"위임 깊이 한도({_MAX_DELEGATION_DEPTH})에 도달했습니다. 위임을 중단합니다."

    get_user_id(config)  # user_id 유효성 검증

    # retrieval_tools 직접 호출로 librarian 역할 수행
    from app.agents.tools.retrieval_tools import search_graph_entities, search_scraps

    lines: list[str] = []

    # 스크랩 검색
    try:
        scrap_results: list[dict[str, Any]] = await search_scraps.ainvoke(  # type: ignore[arg-type]
            {"query": query, "limit": 8},
            config=config,
        )
        if scrap_results:
            lines.append(f"[스크랩 검색 결과: {len(scrap_results)}건]")
            for i, r in enumerate(scrap_results[:5], 1):
                title = r.get("title", "(제목 없음)")
                preview = r.get("content_preview", "")[:150]
                tags = ", ".join(r.get("tags") or [])
                lines.append(f"{i}. {title}")
                if preview:
                    lines.append(f"   {preview}")
                if tags:
                    lines.append(f"   태그: {tags}")
        else:
            lines.append("[스크랩 검색 결과 없음]")
    except Exception:
        logger.exception("delegate_to_librarian: 스크랩 검색 오류 query=%s", query)
        lines.append("[스크랩 검색 중 오류 발생]")

    lines.append("")

    # 그래프 엔티티 검색
    try:
        entity_results: list[dict[str, Any]] = await search_graph_entities.ainvoke(  # type: ignore[arg-type]
            {"keyword": query, "entity_type": "", "limit": 8},
            config=config,
        )
        if entity_results:
            lines.append(f"[그래프 엔티티: {len(entity_results)}건]")
            for i, e in enumerate(entity_results[:5], 1):
                name = e.get("name", "(이름 없음)")
                etype = e.get("type", "")
                lines.append(f"{i}. {name} ({etype})")
        else:
            lines.append("[관련 그래프 엔티티 없음]")
    except Exception:
        logger.exception("delegate_to_librarian: 그래프 검색 오류 query=%s", query)
        lines.append("[그래프 검색 중 오류 발생]")

    if context:
        lines.insert(0, f"[컨텍스트] {context}\n")

    return "\n".join(lines)


@tool
async def delegate_to_analyst(
    query: str,
    context: str = "",
    *,
    config: RunnableConfig,
) -> str:
    """Analyst 에이전트에게 지식 분석 작업을 위임한다.

    커뮤니티 인사이트와 토픽 분포 분석을 직접 수행하여
    결과를 텍스트 형식으로 반환한다.

    Args:
        query: 분석 쿼리 또는 관심 키워드
        context: 추가 컨텍스트 (선택 사항)

    Returns:
        분석 결과를 요약한 텍스트 문자열
    """
    depth = _get_delegation_depth(config)
    if depth >= _MAX_DELEGATION_DEPTH:
        return f"위임 깊이 한도({_MAX_DELEGATION_DEPTH})에 도달했습니다. 위임을 중단합니다."

    get_user_id(config)  # user_id 유효성 검증

    # analysis_tools / stats_tools 직접 호출로 analyst 역할 수행
    from app.agents.tools.analysis_tools import get_community_insights
    from app.agents.tools.stats_tools import get_topic_distribution

    lines: list[str] = []

    # 커뮤니티 인사이트
    try:
        communities: list[dict[str, Any]] = await get_community_insights.ainvoke(  # type: ignore[arg-type]
            {"keyword": query or None, "limit": 5},
            config=config,
        )
        if communities:
            lines.append(f"[커뮤니티 인사이트: {len(communities)}개 클러스터]")
            for i, c in enumerate(communities[:3], 1):
                entities = c.get("entities") or []
                summary = c.get("summary", "")
                size = c.get("size", len(entities))
                lines.append(f"{i}. 엔티티 {size}개 클러스터: {', '.join(entities[:5])}")
                if summary:
                    lines.append(f"   요약: {summary[:200]}")
        else:
            lines.append("[커뮤니티 인사이트 없음]")
    except Exception:
        logger.exception("delegate_to_analyst: 커뮤니티 인사이트 오류 query=%s", query)
        lines.append("[커뮤니티 인사이트 조회 중 오류 발생]")

    lines.append("")

    # 토픽 분포
    try:
        topics: list[dict[str, Any]] = await get_topic_distribution.ainvoke(  # type: ignore[arg-type]
            {"limit": 10},
            config=config,
        )
        if topics:
            lines.append("[토픽 분포 (상위 태그)]")
            for t in topics[:8]:
                tag = t.get("tag", "")
                count = t.get("count", 0)
                lines.append(f"  - {tag}: {count}회")
        else:
            lines.append("[토픽 분포 데이터 없음]")
    except Exception:
        logger.exception("delegate_to_analyst: 토픽 분포 오류")
        lines.append("[토픽 분포 조회 중 오류 발생]")

    if context:
        lines.insert(0, f"[컨텍스트] {context}\n")

    return "\n".join(lines)


@tool
async def delegate_to_curator(
    source_id: str,
    source_type: str,
    content: str,
    *,
    config: RunnableConfig,
) -> dict[str, int]:
    """Curator 에이전트에게 콘텐츠 그래프 저장 작업을 위임한다.

    엔티티 추출 → 관계 추출 → 그래프 저장을 순서대로 수행한다.

    Args:
        source_id: 출처 스크랩 또는 다이어리 ID
        source_type: "scrap" 또는 "diary"
        content: 엔티티/관계를 추출할 텍스트 콘텐츠

    Returns:
        {"entities_saved": N, "relations_saved": N} 형식의 dict
    """
    depth = _get_delegation_depth(config)
    if depth >= _MAX_DELEGATION_DEPTH:
        logger.warning("delegate_to_curator: 위임 깊이 한도 도달, 저장 중단")
        return {"entities_saved": 0, "relations_saved": 0}

    get_user_id(config)  # user_id 유효성 검증

    from app.agents.tools.graph_tools import extract_entities, extract_relations, save_to_graph

    # 1단계: 엔티티 추출
    try:
        entities: list[dict[str, str]] = await extract_entities.ainvoke(  # type: ignore[arg-type]
            {"text": content},
            config=config,
        )
    except Exception:
        logger.exception("delegate_to_curator: 엔티티 추출 오류 source_id=%s", source_id)
        entities = []

    if not entities:
        logger.info("delegate_to_curator: 추출된 엔티티 없음 source_id=%s", source_id)
        return {"entities_saved": 0, "relations_saved": 0}

    # 2단계: 관계 추출
    entity_names = [e.get("name", "") for e in entities if e.get("name")]
    try:
        relations: list[dict[str, str]] = await extract_relations.ainvoke(  # type: ignore[arg-type]
            {"text": content, "entities": entity_names},
            config=config,
        )
    except Exception:
        logger.exception("delegate_to_curator: 관계 추출 오류 source_id=%s", source_id)
        relations = []

    # 3단계: 그래프 저장
    try:
        result: dict[str, int] = await save_to_graph.ainvoke(  # type: ignore[arg-type]
            {
                "source_id": source_id,
                "source_type": source_type,
                "entities": entities,
                "relations": relations,
            },
            config=config,
        )
        return result
    except Exception:
        logger.exception("delegate_to_curator: 그래프 저장 오류 source_id=%s", source_id)
        return {"entities_saved": 0, "relations_saved": 0}
