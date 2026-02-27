import logging
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from app.agents.socrates.state import SocratesState
from app.config.llm import get_analytical_llm

logger = logging.getLogger(__name__)

MAX_RETRIEVAL_ATTEMPTS = 2

BATCH_RELEVANCE_PROMPT = """Rate the relevance of each memory to the query.
For each memory, output its number followed by "yes" or "no".
A memory is relevant if it directly addresses the query topic, provides useful context, or contains information that helps explore the query.

Query: {query}

{numbered_memories}

Output format (one per line):
1: yes
2: no
..."""


async def _grade_relevance(query: str, memories: list[dict]) -> list[dict]:
    """검색된 기억들의 관련성을 LLM으로 평가. 배치 처리로 1회 호출."""
    if not memories:
        return []
    try:
        numbered_lines = []
        for i, mem in enumerate(memories, 1):
            date = mem.get("created_at", "")[:10]
            title = mem.get("title", "Untitled")
            summary = mem.get("summary") or mem.get("content", "")[:300]
            numbered_lines.append(f"{i}. [{date}] {title} — {summary[:200]}")

        prompt_text = BATCH_RELEVANCE_PROMPT.format(
            query=query,
            numbered_memories="\n".join(numbered_lines),
        )
        llm = get_analytical_llm()
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        output = response.content.strip()

        graded = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                try:
                    idx = int(parts[0].strip()) - 1
                    verdict = parts[1].strip().lower()
                    if 0 <= idx < len(memories) and "yes" in verdict:
                        graded.append(memories[idx])
                except (ValueError, IndexError):
                    pass
        return graded
    except Exception:
        logger.warning("Relevance grading 실패, 전체 반환")
        return memories


async def grading_node(state: SocratesState) -> dict:
    """검색 결과 관련성 검증 + 품질 판정 노드.

    defer=True로 등록됨 — memory_retrieval + context_retrieval 둘 다 완료 후 실행.

    graded 있으면 → 'good'
    graded 없고 attempts < MAX → 'retry' (→ memory_retrieval만 재실행)
    그 외(attempts >= MAX) → 'empty'

    루프 가드: retrieval_attempts >= MAX_RETRIEVAL_ATTEMPTS이면 절대 retry 반환하지 않음.
    LLM 실패 시: raw_memories 전체를 그대로 통과.
    """
    writer = get_stream_writer()
    writer({"node": "grading", "status": "started"})

    search_query = state.get("search_query", state["user_query"])
    raw_memories = state.get("raw_memories", [])
    retrieval_attempts = state.get("retrieval_attempts", 0)

    graded = await _grade_relevance(search_query, raw_memories)

    quality: Literal["good", "retry", "empty"]
    if graded:
        quality = "good"
    elif retrieval_attempts < MAX_RETRIEVAL_ATTEMPTS:
        quality = "retry"
    else:
        quality = "empty"

    logger.debug(
        "grading: raw=%d, graded=%d, quality=%s, attempts=%d",
        len(raw_memories),
        len(graded),
        quality,
        retrieval_attempts,
    )

    writer(
        {
            "node": "grading",
            "status": "done",
            "quality": quality,
            "graded": len(graded),
        }
    )

    return {
        "graded_memories": graded,
        "retrieval_quality": quality,
    }
