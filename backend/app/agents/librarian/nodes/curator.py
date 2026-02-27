import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response

logger = logging.getLogger(__name__)

# 토큰 절약을 위한 Curator 입력 텍스트 최대 길이 (약 3000 토큰)
CURATOR_MAX_INPUT_CHARS = 12000

CURATOR_SYSTEM_PROMPT = """You are the Curator of a personal knowledge management AI.
Classify incoming text and generate metadata.

Tasks:
1. Classify: INSIGHT (opinions, essays, analysis) | FACT (docs, manuals, news) | SPAM (ads, nav, irrelevant)
2. Tags: Generate 3-5 specific topic tags in English (e.g., "React", "machine-learning", "startup")
3. Summary: Write a 2-3 sentence summary in Korean capturing key arguments and conclusions.

Example:
Input: "React Server Components allow rendering on the server, reducing client-side JavaScript..."
Output:
{
  "category": "FACT",
  "tags": ["React", "server-components", "performance"],
  "summary": "React Server Components의 개념과 장점을 설명하는 글입니다. 서버 사이드 렌더링을 통해 클라이언트 JavaScript를 줄이고 성능을 개선할 수 있습니다."
}

Return ONLY valid JSON. No markdown. No explanation."""


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
    if len(target_text) > CURATOR_MAX_INPUT_CHARS:
        target_text = target_text[:CURATOR_MAX_INPUT_CHARS] + "\n\n[Content truncated...]"

    base_llm = get_analytical_llm()
    # structured JSON output으로 파싱 실패 최소화
    llm = base_llm.bind(response_format={"type": "json_object"})

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
