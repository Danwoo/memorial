# backend/app/agents/tools/graph_tools.py
"""그래프 도구 모음 — Curator 에이전트 전용 Knowledge Graph tool 7종."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 모듈 레벨 프롬프트 상수
# ---------------------------------------------------------------------------

_EXTRACT_ENTITIES_SYSTEM = """You are a knowledge graph entity extractor.
Extract meaningful named entities from the given text.

Entity Types (use ONLY these):
Concept, Person, Organization, Location, Event, Technology, Product, Topic,
Idea, Company, Platform, Framework, Language, Tool, Project

Rules:
- Skip generic words (today, thing, this, it, something, 것, 이것)
- Use canonical English names when an official one exists (React, not ReactJS/리액트)
- Use original language for proper nouns without standard English translations
- Maximum 15 entities

Return ONLY valid JSON. No markdown code blocks.
{
  "entities": [
    {"name": "...", "type": "..."},
    ...
  ]
}
If no meaningful entities found, return {"entities": []}."""

_EXTRACT_RELATIONS_SYSTEM = """You are a knowledge graph relation extractor.
Given a text and a list of already-extracted entities, identify relationships between them.

Relationship Types (ordered by specificity — prefer specific types):
- Creation: CREATED_BY, BUILT_WITH, DERIVED_FROM, INSPIRED_BY
- Hierarchy: IS_A, PART_OF, CONTAINS, BELONGS_TO
- Usage: USES, USED_BY, USED_FOR, DEPENDS_ON
- Association: WORKS_AT, LOCATED_IN, HAS
- Argumentation: SUPPORTS, CONTRADICTS, LEADS_TO, CAUSED_BY
- Similarity: SIMILAR_TO, OPPOSITE_OF
- General: RELATED_TO (LAST RESORT — use only when no specific type fits)

Directionality: source VERB target.
"TypeScript is created by Microsoft" → source=TypeScript, target=Microsoft, rel_type=CREATED_BY

Maximum 15 relations.

Return ONLY valid JSON. No markdown code blocks.
{
  "relations": [
    {"source": "...", "target": "...", "rel_type": "..."},
    ...
  ]
}
If no meaningful relations found, return {"relations": []}."""

_SUGGEST_CONNECTIONS_SYSTEM = """You are a knowledge graph connection suggester.
Given a list of entity names, suggest potential meaningful connections between them
that are not yet explicitly stated but are plausible based on general knowledge.

For each suggestion, provide:
- source: entity name (must be from the given list)
- target: entity name (must be from the given list)
- rel_type: one of RELATED_TO, PART_OF, CAUSED_BY, DEPENDS_ON, SIMILAR_TO,
  OPPOSITE_OF, DERIVED_FROM, USED_BY, CREATED_BY, WORKS_AT, LOCATED_IN,
  BELONGS_TO, HAS, IS_A, USES, USED_FOR, BUILT_WITH, INSPIRED_BY, CONTAINS,
  SUPPORTS, CONTRADICTS, LEADS_TO
- reason: brief Korean explanation of why this connection makes sense

Maximum 10 suggestions.

Return ONLY valid JSON. No markdown code blocks.
{
  "suggestions": [
    {"source": "...", "target": "...", "rel_type": "...", "reason": "..."},
    ...
  ]
}"""


# ---------------------------------------------------------------------------
# Tool 정의
# ---------------------------------------------------------------------------


@tool
async def extract_entities(
    text: str,
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """텍스트에서 Named Entity를 추출한다.

    Args:
        text: 엔티티를 추출할 텍스트

    Returns:
        {"name": "...", "type": "..."} 형식의 dict 리스트
    """
    base_llm = get_analytical_llm()
    llm = base_llm.bind(response_format={"type": "json_object"})

    messages = [
        SystemMessage(content=_EXTRACT_ENTITIES_SYSTEM),
        HumanMessage(content=text),
    ]

    try:
        response = await llm.ainvoke(messages)
        result = parse_llm_json_response(response.content.strip())
        entities = result.get("entities", [])
        if not isinstance(entities, list):
            return []
        return [
            {"name": str(e.get("name", "")), "type": str(e.get("type", "Concept"))} for e in entities if e.get("name")
        ]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("extract_entities JSON 파싱 실패: %s", e)
        return []
    except Exception as e:
        logger.exception("extract_entities 오류: %s", e)
        return []


@tool
async def extract_relations(
    text: str,
    entities: list[str],
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """텍스트와 이미 추출된 엔티티 목록을 기반으로 관계를 추출한다.

    Args:
        text: 관계를 추출할 텍스트
        entities: 이미 추출된 엔티티 이름 목록

    Returns:
        {"source": "...", "target": "...", "rel_type": "..."} 형식의 dict 리스트
    """
    base_llm = get_analytical_llm()
    llm = base_llm.bind(response_format={"type": "json_object"})

    entities_str = ", ".join(entities) if entities else "(없음)"
    user_content = f"Entities: {entities_str}\n\n---\n{text}"

    messages = [
        SystemMessage(content=_EXTRACT_RELATIONS_SYSTEM),
        HumanMessage(content=user_content),
    ]

    try:
        response = await llm.ainvoke(messages)
        result = parse_llm_json_response(response.content.strip())
        relations = result.get("relations", [])
        if not isinstance(relations, list):
            return []
        return [
            {
                "source": str(r.get("source", "")),
                "target": str(r.get("target", "")),
                "rel_type": str(r.get("rel_type", "RELATED_TO")),
            }
            for r in relations
            if r.get("source") and r.get("target")
        ]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("extract_relations JSON 파싱 실패: %s", e)
        return []
    except Exception as e:
        logger.exception("extract_relations 오류: %s", e)
        return []


@tool
async def save_to_graph(
    source_id: str,
    source_type: str,
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    *,
    config: RunnableConfig,
) -> dict[str, int]:
    """엔티티와 관계를 Knowledge Graph에 저장한다.

    Args:
        source_id: 출처 스크랩 또는 다이어리 ID
        source_type: "scrap" 또는 "diary"
        entities: {"name": "...", "type": "..."} 형식의 엔티티 목록
        relations: {"source": "...", "target": "...", "rel_type": "..."} 형식의 관계 목록

    Returns:
        {"entities_saved": N, "relations_saved": N} 형식의 dict
    """
    user_id = get_user_id(config)
    container = get_agent_container()
    mindmap_repo = container.mindmap_repo

    if not mindmap_repo.is_connected:
        logger.warning("save_to_graph: KuzuDB 미연결 — 저장 건너뜀")
        return {"entities_saved": 0, "relations_saved": 0}

    entities_saved = 0
    relations_saved = 0

    try:
        if entities:
            await mindmap_repo.save_entities(entities, source_id, user_id)
            entities_saved = len(entities)

        if relations:
            # save_relations는 "type" 키를 사용하므로 rel_type → type 변환
            converted_relations = [
                {
                    "source": r.get("source", ""),
                    "target": r.get("target", ""),
                    "type": r.get("rel_type", r.get("type", "RELATED_TO")),
                }
                for r in relations
                if r.get("source") and r.get("target")
            ]
            await mindmap_repo.save_relations(converted_relations)
            relations_saved = len(converted_relations)

        logger.info(
            "save_to_graph 완료: source_id=%s, source_type=%s, entities=%d, relations=%d",
            source_id,
            source_type,
            entities_saved,
            relations_saved,
        )
    except Exception as e:
        logger.exception("save_to_graph 오류: %s", e)

    return {"entities_saved": entities_saved, "relations_saved": relations_saved}


@tool
async def get_ego_graph(
    entity_name: str,
    hops: int = 2,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """엔티티를 중심으로 N-hop 서브그래프를 조회한다.

    Args:
        entity_name: 중심 엔티티 이름
        hops: 탐색 깊이 (기본 2, 최대 3)

    Returns:
        {"nodes": [...], "edges": [...]} 형식의 서브그래프
    """
    user_id = get_user_id(config)
    container = get_agent_container()
    mindmap_repo = container.mindmap_repo

    if not mindmap_repo.is_connected:
        return {"nodes": [], "edges": []}

    try:
        result = await mindmap_repo.get_ego_graph(entity_name, depth=hops, user_id=user_id)
        nodes = result.get("nodes", [])
        # get_ego_graph는 "links" 키를 반환하므로 "edges"로 변환
        edges = result.get("links", result.get("edges", []))
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        logger.exception("get_ego_graph 오류: entity=%s, %s", entity_name, e)
        return {"nodes": [], "edges": []}


@tool
async def get_hub_entities(
    limit: int = 10,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """연결 수 기준 상위 허브 엔티티 목록을 조회한다.

    Args:
        limit: 반환할 최대 엔티티 수 (기본 10)

    Returns:
        {"name": "...", "type": "...", "connection_count": N} 형식의 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()
    mindmap_repo = container.mindmap_repo

    if not mindmap_repo.is_connected:
        return []

    try:
        rows = await mindmap_repo.get_hub_entities(user_id=user_id, limit=limit)
        return [
            {
                "name": str(r.get("name", "")),
                "type": str(r.get("type", "Concept")),
                "connection_count": int(r.get("connection_count", r.get("degree", 0))),
            }
            for r in rows
            if r.get("name")
        ]
    except Exception as e:
        logger.exception("get_hub_entities 오류: %s", e)
        return []


@tool
async def get_orphan_entities(
    limit: int = 20,
    *,
    config: RunnableConfig,
) -> list[dict[str, Any]]:
    """연결이 없는 고아 엔티티 목록을 조회한다.

    Args:
        limit: 반환할 최대 엔티티 수 (기본 20)

    Returns:
        {"name": "...", "type": "..."} 형식의 dict 리스트
    """
    user_id = get_user_id(config)
    container = get_agent_container()
    mindmap_repo = container.mindmap_repo

    if not mindmap_repo.is_connected:
        return []

    try:
        rows = await mindmap_repo.get_orphan_entities(user_id=user_id, limit=limit)
        return [
            {
                "name": str(r.get("name", "")),
                "type": str(r.get("type", "Concept")),
            }
            for r in rows
            if r.get("name")
        ]
    except Exception as e:
        logger.exception("get_orphan_entities 오류: %s", e)
        return []


@tool
async def suggest_connections(
    entity_names: list[str],
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """엔티티 목록을 기반으로 잠재적 연결 관계를 LLM이 제안한다.

    Args:
        entity_names: 연결 제안 대상 엔티티 이름 목록

    Returns:
        {"source": "...", "target": "...", "rel_type": "...", "reason": "..."} 형식의 dict 리스트
    """
    if not entity_names:
        return []

    base_llm = get_analytical_llm()
    llm = base_llm.bind(response_format={"type": "json_object"})

    entities_str = "\n".join(f"- {name}" for name in entity_names)
    user_content = f"Entities:\n{entities_str}"

    messages = [
        SystemMessage(content=_SUGGEST_CONNECTIONS_SYSTEM),
        HumanMessage(content=user_content),
    ]

    try:
        response = await llm.ainvoke(messages)
        result = parse_llm_json_response(response.content.strip())
        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            return []
        return [
            {
                "source": str(s.get("source", "")),
                "target": str(s.get("target", "")),
                "rel_type": str(s.get("rel_type", "RELATED_TO")),
                "reason": str(s.get("reason", "")),
            }
            for s in suggestions
            if s.get("source") and s.get("target")
        ]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning("suggest_connections JSON 파싱 실패: %s", e)
        return []
    except Exception as e:
        logger.exception("suggest_connections 오류: %s", e)
        return []


@tool
async def find_path_between_entities(
    source_entity: str,
    target_entity: str,
    max_hops: int = 3,
    *,
    config: RunnableConfig,
) -> dict[str, Any]:
    """두 엔티티 사이의 최단 그래프 경로(shortest path)를 찾아 reasoning trace를 제공한다.

    추천 설명(explainability)이나 두 개념의 연결 분석에 사용한다.
    예: "왜 이 스크랩이 추천됐어요?" → 경로로 답변 가능.

    Args:
        source_entity: 시작 엔티티 이름 (정확한 이름)
        target_entity: 목표 엔티티 이름 (정확한 이름)
        max_hops: 최대 경로 길이 (1-3, 기본 3)

    Returns:
        found: 경로 발견 여부
        path: 엔티티 시퀀스 (예: ["React", "JavaScript", "Frontend"])
        rel_types: 관계 타입 시퀀스 (예: ["USES", "PART_OF"])
        hops: 경로 길이
        explanation: 한국어 설명 문자열
    """
    user_id = get_user_id(config)
    container = get_agent_container()

    result = await container.mindmap_repo.find_shortest_path(
        source=source_entity,
        target=target_entity,
        user_id=user_id,
        max_hops=min(max(max_hops, 1), 3),
    )

    if result is None:
        return {
            "found": False,
            "message": f"'{source_entity}'와 '{target_entity}' 사이 경로를 찾을 수 없습니다.",
        }

    names: list[str] = result.get("names", []) or []
    rel_types: list[str] = result.get("rel_types", []) or []

    # 사람이 읽기 좋은 설명 조립 (A →(USES)→ B →(PART_OF)→ C)
    segments = []
    for i, rel in enumerate(rel_types):
        if i + 1 < len(names):
            segments.append(f"{names[i]} →({rel})→ {names[i + 1]}")

    return {
        "found": True,
        "path": names,
        "rel_types": rel_types,
        "hops": result.get("hops", len(rel_types)),
        "explanation": " ".join(segments) if segments else " → ".join(names),
    }
