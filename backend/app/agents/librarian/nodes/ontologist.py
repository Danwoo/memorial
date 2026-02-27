from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response

# 토큰 절약을 위한 Ontologist 입력 텍스트 최대 길이 (약 1500 토큰)
ONTOLOGIST_MAX_INPUT_CHARS = 6000

ONTOLOGIST_SYSTEM_PROMPT = """You are the Ontologist for a personal knowledge management system.
Extract meaningful entities and their relationships to build a knowledge graph.

**Step 1 — Identify Entities:**
Extract specific, named concepts. Skip generic words (today, thing, this, it, something).

Entity Types (use ONLY these):
- Person, Organization, Company
- Technology, Framework, Language, Tool, Platform, Product
- Concept, Idea, Topic
- Event, Location, Project

Normalization: Use canonical English names when an official one exists (React, not ReactJS/리액트).
Use original language for proper nouns without standard English translations.

**Step 2 — Identify Relationships:**
For each pair of related entities, choose the MOST SPECIFIC relationship type.

Relationship Types (ordered by specificity — prefer types at the top):
- Creation: CREATED_BY, BUILT_WITH, DERIVED_FROM, INSPIRED_BY
- Hierarchy: IS_A, PART_OF, CONTAINS, BELONGS_TO
- Usage: USES, USED_BY, USED_FOR, DEPENDS_ON
- Association: WORKS_AT, LOCATED_IN, HAS, MENTIONS
- Argumentation: SUPPORTS, CONTRADICTS, LEADS_TO, CAUSED_BY
- Similarity: SIMILAR_TO, OPPOSITE_OF
- General: RELATED_TO (LAST RESORT — use only when no specific type fits)

Directionality: source VERB target. "TypeScript is created by Microsoft" → source=TypeScript, target=Microsoft, type=CREATED_BY.

**Limits:** Maximum 15 entities and 15 relations.

**Example Input:**
"TypeScript는 Microsoft가 만든 JavaScript의 superset이다. React 프로젝트에서 많이 쓰이며,
Next.js는 React 위에 서버 사이드 렌더링을 제공한다."

**Example Output:**
{
  "entities": [
    {"name": "TypeScript", "type": "Language"},
    {"name": "Microsoft", "type": "Company"},
    {"name": "JavaScript", "type": "Language"},
    {"name": "React", "type": "Framework"},
    {"name": "Next.js", "type": "Framework"}
  ],
  "relations": [
    {"source": "TypeScript", "target": "Microsoft", "type": "CREATED_BY"},
    {"source": "TypeScript", "target": "JavaScript", "type": "DERIVED_FROM"},
    {"source": "React", "target": "TypeScript", "type": "USES"},
    {"source": "Next.js", "target": "React", "type": "BUILT_WITH"}
  ]
}

Return ONLY valid JSON. No markdown code blocks. No explanation.
If no meaningful entities found, return {"entities": [], "relations": []}."""


async def ontologist_node(state: AgentState) -> dict:
    """Ontologist 노드: 콘텐츠에서 엔티티 및 관계 추출.

    Args:
        state: target_text, summary, tags를 포함한 에이전트 상태

    Returns:
        extracted_entities, extracted_relations, next_step을 포함한 dict
    """
    target_text = state.get("target_text", "")
    summary = state.get("summary", "")
    tags = state.get("tags", [])

    if not target_text:
        return {"extracted_entities": [], "extracted_relations": [], "next_step": "save"}

    if len(target_text) > ONTOLOGIST_MAX_INPUT_CHARS:
        target_text = target_text[:ONTOLOGIST_MAX_INPUT_CHARS] + "\n\n[Content truncated...]"

    # Curator 분석 결과를 힌트로 활용
    context_hint = ""
    if summary:
        context_hint += f"Summary: {summary}\n"
    if tags:
        context_hint += f"Tags: {', '.join(tags)}\n"

    base_llm = get_analytical_llm()
    # structured JSON output으로 파싱 실패 최소화
    llm = base_llm.bind(response_format={"type": "json_object"})

    user_content = f"""Analyze this content and extract entities/relations:

{context_hint}
---
{target_text}"""

    messages = [SystemMessage(content=ONTOLOGIST_SYSTEM_PROMPT), HumanMessage(content=user_content)]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        result = parse_llm_json_response(content)

        entities = result.get("entities", [])
        relations = result.get("relations", [])

        return {"extracted_entities": entities, "extracted_relations": relations, "next_step": "save"}

    except (ValueError, KeyError) as e:
        return {
            "extracted_entities": [],
            "extracted_relations": [],
            "next_step": "save",
            "error": f"JSON parse error: {str(e)}",
        }
    except Exception as e:
        return {"extracted_entities": [], "extracted_relations": [], "next_step": "save", "error": str(e)}
