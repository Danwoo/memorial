import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response

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
    """Curator 노드: 콘텐츠 분류 및 태그/요약 생성.

    Args:
        state: target_text를 포함한 에이전트 상태

    Returns:
        classification, tags, summary, next_step을 포함한 dict
    """
    target_text = state.get("target_text", "")

    if not target_text:
        return {
            "classification": "SPAM",
            "summary": "Empty content",
            "tags": [],
            "next_step": "end",
            "error": "No target text provided",
        }

    # URL 입력 감지 시 웹 콘텐츠 스크래핑
    source_url = None
    if target_text.startswith("http://") or target_text.startswith("https://"):
        from app.services.ingest_service import process_web_content

        logger.info("Curator detected URL: %s", target_text)
        scraped_data = await process_web_content(target_text)

        source_url = target_text
        target_text = f"Title: {scraped_data['title']}\n\nContent:\n{scraped_data['content']}"
        state["source_url"] = source_url

    # 토큰 절약을 위한 길이 제한
    max_chars = 12000
    if len(target_text) > max_chars:
        target_text = target_text[:max_chars] + "\n\n[Content truncated...]"

    llm = get_analytical_llm()

    messages = [
        SystemMessage(content=CURATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze this content:\n\n{target_text}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        result = parse_llm_json_response(content)

        category = result.get("category", "FACT")
        tags = result.get("tags", [])
        summary = result.get("summary", "")

        next_step = "end" if category == "SPAM" else "ontologist"

        return {"classification": category, "tags": tags, "summary": summary, "next_step": next_step}

    except (ValueError, KeyError) as e:
        return {
            "classification": "FACT",
            "tags": [],
            "summary": "Failed to parse classification",
            "next_step": "save",
            "error": f"JSON parse error: {str(e)}",
        }
    except Exception as e:
        return {
            "classification": "FACT",
            "tags": [],
            "summary": "Error during classification",
            "next_step": "save",
            "error": str(e),
        }
