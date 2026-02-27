from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SocratesState(TypedDict):
    """Socrates 6노드 파이프라인 상태.

    각 필드 그룹이 담당 노드와 1:1 매핑된다.
    messages는 add_messages 리듀서를 사용하여 중복 없이 병합된다 (v1.0).
    """

    # 입력 (SocratesService가 초기화)
    messages: Annotated[list[BaseMessage], add_messages]  # operator.add 대신 add_messages 리듀서 사용
    user_id: str
    session_id: str
    user_query: str
    turn_count: int
    source_context: dict | None
    explicit_mode: str | None

    # query_understanding 출력
    detected_mode: str | None
    rewritten_queries: list[str]
    search_query: str

    # memory_retrieval 출력
    raw_memories: list[dict]
    retrieval_attempts: int

    # context_retrieval 출력
    graph_context: str
    diary_context: str
    community_context: str

    # grading 출력 (defer=True — memory_retrieval + context_retrieval 완료 후 실행)
    graded_memories: list[dict]
    retrieval_quality: Literal["good", "retry", "empty"]

    # enrichment 출력
    formatted_memories: str
    contradiction_context: str
    connection_suggestion: str
    user_profile: dict | None
    previous_session_context: str
    topic_session_context: str

    # context_assembly 출력
    system_prompt: str
    llm_messages: list[BaseMessage]
    references: list[dict]

    # 제어
    next_step: str | None
    error: str | None


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
