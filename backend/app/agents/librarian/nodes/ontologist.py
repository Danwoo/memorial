"""
Ontologist Node - Entity & Relation Extraction
Based on Agent_Design_Spec.md - Section 2.3

The Ontologist builds the Knowledge Graph by:
1. Extracting high-level entities (concepts, people, projects)
2. Defining relationships between entities
3. Using canonical names for deduplication
"""

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
    """
    Ontologist Node: Extracts entities and relations from content.

    Input: state.target_text, state.summary
    Output: extracted_entities, extracted_relations, next_step
    """
    # Get target text and context from state
    target_text = state.get("target_text", "")
    summary = state.get("summary", "")
    tags = state.get("tags", [])

    if not target_text:
        return {"extracted_entities": [], "extracted_relations": [], "next_step": "save"}

    # Truncate if too long
    max_chars = 6000
    if len(target_text) > max_chars:
        target_text = target_text[:max_chars] + "\n\n[Content truncated...]"

    # Create context hint from curator's analysis
    context_hint = ""
    if summary:
        context_hint += f"Summary: {summary}\n"
    if tags:
        context_hint += f"Tags: {', '.join(tags)}\n"

    # Get shared LLM instance
    llm = get_analytical_llm()

    # Build messages
    user_content = f"""Analyze this content and extract entities/relations:

{context_hint}
---
{target_text}"""

    messages = [SystemMessage(content=ONTOLOGIST_SYSTEM_PROMPT), HumanMessage(content=user_content)]

    try:
        # Call LLM
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON response (strips markdown code fences)
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
