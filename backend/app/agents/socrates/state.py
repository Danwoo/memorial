from langchain_core.messages import BaseMessage

from app.agents.base_state import ChatPipelineState


class SocratesState(ChatPipelineState):
    """Socrates 다이어리 전문 에이전트 상태.

    ChatPipelineState를 상속. 현재는 추가 필드 없음.
    향후 emotion_tracking, cognitive_patterns 등 Socrates 전용 필드 확장 예정.
    """


def build_socrates_initial_state(
    messages: list[BaseMessage],
    user_id: str,
    session_id: str,
    user_query: str,
    turn_count: int,
    mode: str | None = None,
    source_context: dict | None = None,
) -> SocratesState:
    """Socrates 그래프 실행을 위한 초기 상태 생성.

    Args:
        messages: 전체 대화 이력 (HumanMessage + AIMessage)
        user_id: 소유 사용자 ID (str)
        session_id: 현재 세션 ID (str)
        user_query: 현재 턴 사용자 메시지 원문
        turn_count: HumanMessage 누적 수
        mode: 명시적 대화 모드 (없으면 None → query_understanding에서 자동 분류)
        source_context: 현재 화면 컨텍스트 (스크랩/다이어리 정보)
    """
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
