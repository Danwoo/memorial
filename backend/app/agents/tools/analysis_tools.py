# backend/app/agents/tools/analysis_tools.py
"""지식 분석 도구 모음 — 커뮤니티 인사이트, 연결 탐색, 콘텐츠 비교, 타임라인 분석."""

from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id
from app.config.llm import get_analytical_llm


@tool
async def get_community_insights(
    keyword: str | None = None,
    limit: int = 5,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """사용자 지식 그래프의 커뮤니티(클러스터) 요약 인사이트를 반환한다.

    Args:
        keyword: 특정 키워드로 커뮤니티 필터링 (None이면 전체 반환)
        limit: 반환할 최대 커뮤니티 수 (기본 5)

    Returns:
        entities, entity_types, size, summary 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    summaries = await container.community_summary.get_community_summaries(user_id)

    if keyword:
        kw_lower = keyword.lower()
        summaries = [
            s
            for s in summaries
            if any(kw_lower in e.lower() for e in s.get("entities", [])) or kw_lower in s.get("summary", "").lower()
        ]

    return summaries[:limit]


@tool
async def find_connections(
    topic_a: str,
    topic_b: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """두 주제(엔티티) 사이의 공통 연결 엔티티와 관계 경로를 탐색한다.

    Args:
        topic_a: 첫 번째 주제/엔티티 이름
        topic_b: 두 번째 주제/엔티티 이름

    Returns:
        common_entities, connection_path, similarity_score 필드를 가진 dict
    """
    get_user_id(config)  # user_id 유효성 검증
    container = get_agent_container()

    related_a = await container.mindmap_repo.get_related_context(topic=topic_a, depth=2)
    related_b = await container.mindmap_repo.get_related_context(topic=topic_b, depth=2)

    names_a = {r.get("name", "") for r in related_a if r.get("name")}
    names_b = {r.get("name", "") for r in related_b if r.get("name")}
    names_a.add(topic_a)
    names_b.add(topic_b)

    common = list(names_a & names_b - {topic_a, topic_b})

    # 연결 경로: topic_a → common → topic_b 형태로 단순 표현
    connection_path: list[str] = []
    if common:
        connection_path = [topic_a, common[0], topic_b]
    elif topic_a in names_b or topic_b in names_a:
        connection_path = [topic_a, topic_b]

    # 유사도: 자카드 유사도 (공통 / 전체)
    union_size = len(names_a | names_b)
    similarity = len(names_a & names_b) / union_size if union_size > 0 else 0.0

    return {
        "common_entities": common[:10],
        "connection_path": connection_path,
        "similarity_score": round(similarity, 4),
    }


@tool
async def compare_content(
    content_a: str,
    content_b: str,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """두 텍스트 콘텐츠를 LLM으로 비교 분석하여 유사점, 차이점, 결론을 반환한다.

    Args:
        content_a: 첫 번째 비교 대상 텍스트
        content_b: 두 번째 비교 대상 텍스트

    Returns:
        similarities, differences, conclusion 필드를 가진 dict
    """
    get_user_id(config)  # user_id 유효성 검증

    system_prompt = """두 텍스트를 분석하여 JSON 형식으로 비교 결과를 반환하라.
반드시 다음 형식으로만 응답하라:
{
  "similarities": ["공통점1", "공통점2"],
  "differences": ["차이점1", "차이점2"],
  "conclusion": "전반적인 비교 결론 한 문장"
}"""
    user_prompt = f"텍스트 A:\n{content_a[:1000]}\n\n텍스트 B:\n{content_b[:1000]}"

    try:
        llm = get_analytical_llm()
        response = await llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        import json

        text = response.content.strip()
        # JSON 블록 추출
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return {
            "similarities": result.get("similarities", []),
            "differences": result.get("differences", []),
            "conclusion": result.get("conclusion", ""),
        }
    except Exception:
        return {
            "similarities": [],
            "differences": [],
            "conclusion": "비교 분석 중 오류가 발생했습니다.",
        }


@tool
async def get_entity_timeline(
    entity_name: str,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """Knowledge Graph 엔티티가 언급된 스크랩들의 시간순 목록을 반환한다.

    Args:
        entity_name: 타임라인을 조회할 엔티티 이름
        limit: 최대 반환 결과 수 (기본 20)

    Returns:
        date, source_type, source_id, title_preview 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 엔티티 → Memory(스크랩) ID 목록 조회
    scrap_refs = await container.mindmap_repo.search_memories_by_entities(
        entity_names=[entity_name],
        user_id=user_id,
        limit=limit,
    )

    if not scrap_refs:
        return []

    scrap_ids = [UUID(r["scrap_id"]) for r in scrap_refs if r.get("scrap_id")]
    if not scrap_ids:
        return []

    # 스크랩 상세 조회
    results: list[dict[str, Any]] = []
    for scrap_id in scrap_ids[:limit]:
        try:
            scrap = await container.scrap_repo.get_by_id(scrap_id, UUID(user_id))
            if scrap:
                results.append(
                    {
                        "date": scrap.created_at.isoformat() if scrap.created_at else "",
                        "source_type": scrap.source_type,
                        "source_id": str(scrap.id),
                        "title_preview": (scrap.title or "")[:80],
                    }
                )
        except Exception:
            continue

    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results


@tool
async def get_content_timeline(
    topic: str,
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """특정 토픽과 관련된 스크랩 + 다이어리를 시간순으로 반환한다.

    Args:
        topic: 검색 토픽 키워드
        limit: 최대 반환 결과 수 (기본 20)

    Returns:
        date, source_type, title, preview 필드를 가진 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    # 스크랩 검색
    scrap_results = await container.hybrid_search.search(
        user_id=UUID(user_id),
        query=topic,
        limit=limit // 2 + 1,
    )

    # 다이어리 검색
    diary_results = await container.diary_repo.search_diaries(
        query=topic,
        user_id=user_id,
        limit=limit // 2 + 1,
    )

    timeline: list[dict[str, Any]] = []

    for s in scrap_results:
        content = s.get("content") or ""
        timeline.append(
            {
                "date": s.get("created_at", ""),
                "source_type": "scrap",
                "title": s.get("title", ""),
                "preview": content[:200],
            }
        )

    for d in diary_results:
        content = d.get("content") or ""
        timeline.append(
            {
                "date": d.get("created_at", ""),
                "source_type": "diary",
                "title": d.get("title") or content[:40],
                "preview": content[:200],
            }
        )

    timeline.sort(key=lambda x: x.get("date", ""), reverse=True)
    return timeline[:limit]
