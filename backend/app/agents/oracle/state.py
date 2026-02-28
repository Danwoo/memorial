from langchain_core.messages import BaseMessage

from app.agents.base_state import ChatPipelineState


class OracleState(ChatPipelineState):
    """Oracle 범용 대화 에이전트 상태.

    ChatPipelineState를 상속. 현재는 추가 필드 없음.
    향후 agent_switch_suggestion 등 Oracle 전용 필드 확장 예정.
    """


def build_oracle_initial_state(
    messages: list[BaseMessage],
    user_id: str,
    session_id: str,
    user_query: str,
    turn_count: int,
    mode: str | None = None,
    source_context: dict | None = None,
) -> OracleState:
    """Oracle 그래프 실행을 위한 초기 상태 생성."""
    return {
        "messages": messages,
        "user_id": user_id,
        "session_id": session_id,
        "user_query": user_query,
        "turn_count": turn_count,
        "source_context": source_context,
        "explicit_mode": mode,
        "detected_mode": None,
        "rewritten_queries": [],
        "search_query": user_query,
        "retrieval_plan": "full_rag",
        "raw_memories": [],
        "retrieval_attempts": 0,
        "graph_context": "",
        "diary_context": "",
        "community_context": "",
        "graded_memories": [],
        "retrieval_quality": "empty",
        "formatted_memories": "",
        "contradiction_context": "",
        "connection_suggestion": "",
        "user_profile": None,
        "previous_session_context": "",
        "topic_session_context": "",
        "system_prompt": "",
        "llm_messages": [],
        "references": [],
        "next_step": None,
        "error": None,
    }
