from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response

ONTOLOGIST_SYSTEM_PROMPT = """You are the Ontologist. You build the Knowledge Graph.

**Input:**
- Text content labeled as 'INSIGHT' or 'FACT'.

**Goal:**
Extract meaningful Entities and Relationships to expand the user's Ontology.

**Extraction Rules:**
1. **Entities**: Extract ONLY high-level concepts, people, or projects. (No generic words like 'today', 'thing').
   - Types: Concept, Person, Project, Technology, Company, Event
2. **Relations**: Define how A relates to B. Use specific verbs:
   - SUPPORTS, CONTRADICTS, USES, CREATED_BY, PART_OF, RELATED_TO, LEADS_TO, SIMILAR_TO
3. **Deduplication**: Use canonical names. (e.g., 'ReactJS' -> 'React', 'Sam Altman' -> 'Sam Altman').
4. **Limit**: Extract at most 10 entities and 10 relations.

**Output Schema (JSON only, no markdown):**
{
  "entities": [{"name": "React", "type": "Technology"}, {"name": "Meta", "type": "Company"}],
  "relations": [{"source": "React", "target": "Frontend", "type": "USED_FOR"}]
}

IMPORTANT: Return ONLY valid JSON. No explanation, no markdown code blocks.
If no meaningful entities/relations found, return empty arrays."""


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

    # 길이 제한
    max_chars = 6000
    if len(target_text) > max_chars:
        target_text = target_text[:max_chars] + "\n\n[Content truncated...]"

    # Curator 분석 결과를 힌트로 활용
    context_hint = ""
    if summary:
        context_hint += f"Summary: {summary}\n"
    if tags:
        context_hint += f"Tags: {', '.join(tags)}\n"

    llm = get_analytical_llm()

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
