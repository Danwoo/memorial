"""
Curator Node - Content Classification & Tagging
Based on Agent_Design_Spec.md - Section 2.2

The Curator is the "Gatekeeper" that:
1. Classifies content (INSIGHT / FACT / SPAM)
2. Generates tags
3. Creates a one-line summary
"""
import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_analytical_llm

logger = logging.getLogger(__name__)

CURATOR_SYSTEM_PROMPT = """You are the Curator of Memoir AI. Your job is to classify and evaluate incoming text.

**Input:**
- A piece of raw text from a website or PDF.

**Your Tasks:**
1. **Classify**: Determine the type of this content independently.
   - `INSIGHT`: Opinionated articles, essays, thoughts. (High Value -> Pass to Ontologist)
   - `FACT`: Documentation, Manuals, News reports. (Medium Value -> Save as is)
   - `SPAM`: Ads, Navbars, Irrelevant text. (Low Value -> Discard)
2. **Tagging**: Generate 3-5 consistent tags (e.g., "AI", "React", "Startup").
3. **Summary**: Create a one-line summary focused on "Key Idea".

**Output Schema (JSON only, no markdown):**
{
  "category": "INSIGHT" | "FACT" | "SPAM",
  "tags": ["tag1", "tag2"],
  "summary": "One line summary here..."
}

IMPORTANT: Return ONLY valid JSON. No explanation, no markdown code blocks."""


async def curator_node(state: AgentState) -> dict:
    """
    Curator Node: Classifies content and generates tags/summary.

    Input: state.target_text
    Output: classification, tags, summary, next_step
    """
    # Get target text from state
    target_text = state.get("target_text", "")

    if not target_text:
        return {
            "classification": "SPAM",
            "summary": "Empty content",
            "tags": [],
            "next_step": "end",
            "error": "No target text provided"
        }

    # Detect if input is a URL
    source_url = None
    if target_text.startswith("http://") or target_text.startswith("https://"):
        from app.services.ingest_service import process_web_content

        logger.info("Curator detected URL: %s", target_text)
        scraped_data = await process_web_content(target_text)

        source_url = target_text
        # Update target_text with scraped content
        target_text = f"Title: {scraped_data['title']}\n\nContent:\n{scraped_data['content']}"
        state["source_url"] = source_url  # Save URL to state

    # Truncate if too long (save tokens)
    max_chars = 12000 # Increased limit
    if len(target_text) > max_chars:
        target_text = target_text[:max_chars] + "\n\n[Content truncated...]"

    # Get shared LLM instance
    llm = get_analytical_llm()

    # Build messages
    messages = [
        SystemMessage(content=CURATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this content:\n\n{target_text}")
    ]

    try:
        # Call LLM
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)

        category = result.get("category", "FACT")
        tags = result.get("tags", [])
        summary = result.get("summary", "")

        # Determine next step based on classification
        if category == "SPAM":
            next_step = "end"
        elif category == "INSIGHT":
            next_step = "ontologist"
        else:  # FACT
            next_step = "save"

        return {
            "classification": category,
            "tags": tags,
            "summary": summary,
            "next_step": next_step
        }

    except json.JSONDecodeError as e:
        return {
            "classification": "FACT",
            "tags": [],
            "summary": "Failed to parse classification",
            "next_step": "save",
            "error": f"JSON parse error: {str(e)}"
        }
    except Exception as e:
        return {
            "classification": "FACT",
            "tags": [],
            "summary": "Error during classification",
            "next_step": "save",
            "error": str(e)
        }
