from langchain_core.messages import BaseMessage, SystemMessage


def build_references(graded_memories: list[dict], max_count: int = 5) -> list[dict]:
    """graded_memories → 프론트엔드용 reference 리스트 (최대 max_count개)."""
    return [
        {
            "id": str(m.get("id", "")),
            "title": m.get("title", ""),
            "source_type": m.get("source_type", "NOTE"),
            "created_at": str(m.get("created_at", ""))[:10],
        }
        for m in graded_memories[:max_count]
    ]


def build_llm_messages(system_prompt: str, messages: list[BaseMessage]) -> list[BaseMessage]:
    """system_prompt + 대화 이력 → LLM 호출용 메시지 리스트."""
    return [SystemMessage(content=system_prompt), *messages]
