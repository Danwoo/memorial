# backend/app/agents/tools/graph_tools.py
"""그래프 도구 모음 — Knowledge Graph tool 세트.

structured output (Pydantic schema)으로 LLM 응답 형식 강제 + few-shot examples로 정확도 향상.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.container import get_agent_container
from app.agents.tools._context import get_user_id
from app.agents.tools.graph_schemas import (
    ConnectionSuggestionResult,
    EntityExtractionResult,
    RelationExtractionResult,
)
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response  # noqa: F401  (suggest_connections에서 fallback parse용)

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
- For purely emotional/journaling content without proper nouns, return empty list

Few-shot examples:

Input: "TypeScript는 Microsoft가 2012년에 발표한 정적 타입 언어입니다"
Output:
- entities: [
    {"name": "TypeScript", "type": "Language"},
    {"name": "Microsoft", "type": "Company"}
  ]

Input: "React Server Components allow rendering on the server, reducing JavaScript bundle size"
Output:
- entities: [
    {"name": "React Server Components", "type": "Technology"},
    {"name": "React", "type": "Framework"},
    {"name": "JavaScript", "type": "Language"}
  ]

Input: "오늘 발표 망쳐서 너무 부끄러웠다. 다시는 발표 안 하고 싶다."
Output:
- entities: []  # 감정 일기, 추출할 named entity 없음

Input: "Anthropic의 Claude 모델이 LangChain과 잘 통합된다"
Output:
- entities: [
    {"name": "Anthropic", "type": "Company"},
    {"name": "Claude", "type": "Product"},
    {"name": "LangChain", "type": "Framework"}
  ]"""

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
Only use entity names that appear in the provided entity list.

Few-shot examples:

Text: "TypeScript는 Microsoft가 만들었습니다"
Entities: ["TypeScript", "Microsoft"]
Output:
- relations: [
    {"source": "TypeScript", "target": "Microsoft", "rel_type": "CREATED_BY"}
  ]

Text: "React는 컴포넌트 기반 UI 라이브러리이고, JSX를 사용합니다"
Entities: ["React", "JSX", "UI 라이브러리"]
Output:
- relations: [
    {"source": "React", "target": "UI 라이브러리", "rel_type": "IS_A"},
    {"source": "React", "target": "JSX", "rel_type": "USES"}
  ]

Text: "발표를 망쳤지만 다음에는 잘 할 거야"
Entities: []
Output:
- relations: []  # 추출할 관계 없음 (엔티티 없음)

Text: "Anthropic의 Claude는 LangChain과 통합되어 RAG 시스템을 만든다"
Entities: ["Anthropic", "Claude", "LangChain", "RAG"]
Output:
- relations: [
    {"source": "Claude", "target": "Anthropic", "rel_type": "CREATED_BY"},
    {"source": "Claude", "target": "LangChain", "rel_type": "USED_BY"},
    {"source": "LangChain", "target": "RAG", "rel_type": "USED_FOR"}
  ]"""

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
    """텍스트에서 Named Entity를 추출한다 (Pydantic structured output).

    Args:
        text: 엔티티를 추출할 텍스트

    Returns:
        {"name": "...", "type": "..."} 형식의 dict 리스트
    """
    llm = get_analytical_llm().with_structured_output(EntityExtractionResult)

    messages = [
        SystemMessage(content=_EXTRACT_ENTITIES_SYSTEM),
        HumanMessage(content=text),
    ]

    try:
        result: EntityExtractionResult = await llm.ainvoke(messages)
        return [
            {"name": e.name, "type": e.type}
            for e in result.entities
            if e.name and e.name.strip()
        ]
    except Exception:
        # structured output 실패 — fallback으로 JSON 모드 시도하지 않고 안전하게 빈 결과
        # (이미 schema 강제했으므로 실패 시엔 LLM 호출 자체 문제)
        logger.exception("extract_entities 호출 실패")
        return []


@tool
async def extract_relations(
    text: str,
    entities: list[str],
    *,
    config: RunnableConfig,
) -> list[dict[str, str]]:
    """텍스트와 이미 추출된 엔티티 목록을 기반으로 관계를 추출한다 (Pydantic structured output).

    Args:
        text: 관계를 추출할 텍스트
        entities: 이미 추출된 엔티티 이름 목록

    Returns:
        {"source": "...", "target": "...", "rel_type": "..."} 형식의 dict 리스트
    """
    llm = get_analytical_llm().with_structured_output(RelationExtractionResult)

    entities_str = ", ".join(entities) if entities else "(없음)"
    user_content = f"Entities: {entities_str}\n\n---\n{text}"

    messages = [
        SystemMessage(content=_EXTRACT_RELATIONS_SYSTEM),
        HumanMessage(content=user_content),
    ]

    try:
        result: RelationExtractionResult = await llm.ainvoke(messages)
        return [
            {"source": r.source, "target": r.target, "rel_type": r.rel_type}
            for r in result.relations
            if r.source and r.target
        ]
    except Exception:
        logger.exception("extract_relations 호출 실패")
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
    """엔티티 목록을 기반으로 잠재적 연결 관계를 LLM이 제안한다 (Pydantic structured output).

    Args:
        entity_names: 연결 제안 대상 엔티티 이름 목록

    Returns:
        {"source": "...", "target": "...", "rel_type": "...", "reason": "..."} 형식의 dict 리스트
    """
    if not entity_names:
        return []

    llm = get_analytical_llm().with_structured_output(ConnectionSuggestionResult)

    entities_str = "\n".join(f"- {name}" for name in entity_names)
    user_content = f"Entities:\n{entities_str}"

    messages = [
        SystemMessage(content=_SUGGEST_CONNECTIONS_SYSTEM),
        HumanMessage(content=user_content),
    ]

    try:
        result: ConnectionSuggestionResult = await llm.ainvoke(messages)
        return [
            {
                "source": s.source,
                "target": s.target,
                "rel_type": s.rel_type,
                "reason": s.reason,
            }
            for s in result.suggestions
            if s.source and s.target
        ]
    except Exception:
        logger.exception("suggest_connections 호출 실패")
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
