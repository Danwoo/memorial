from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BaseAgentState(TypedDict):
    """모든 채팅 에이전트가 공유하는 기본 상태 필드.

    입력 + 최종 출력 필드만 포함. 파이프라인 중간 상태는 ChatPipelineState에 정의.
    """

    # 입력 (에이전트 서비스가 초기화)
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    user_query: str
    turn_count: int
    source_context: dict | None
    explicit_mode: str | None

    # 최종 출력 (assembly 노드가 채움)
    system_prompt: str
    llm_messages: list[BaseMessage]
    references: list[dict]

    # 제어
    error: str | None


class ChatPipelineState(BaseAgentState):
    """RAG 파이프라인 공통 중간 상태.

    BaseAgentState를 상속하여 모든 retrieval → grading → enrichment → assembly 노드가
    공유하는 파이프라인 필드를 추가한다.
    """

    # query_understanding 출력
    detected_mode: str | None
    rewritten_queries: list[str]
    search_query: str

    # 동적 검색 전략 (query_planner 출력)
    retrieval_plan: str

    # memory_retrieval 출력
    raw_memories: list[dict]
    retrieval_attempts: int

    # context_retrieval 출력
    graph_context: str
    diary_context: str
    community_context: str

    # grading 출력 (defer=True — retrieval 노드 완료 후 실행)
    graded_memories: list[dict]
    retrieval_quality: Literal["good", "retry", "empty"]

    # enrichment 출력
    formatted_memories: str
    contradiction_context: str
    connection_suggestion: str
    user_profile: dict | None
    previous_session_context: str
    topic_session_context: str

    # 제어 (파이프라인 흐름)
    next_step: str | None
