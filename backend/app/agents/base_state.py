from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class BaseAgentState(TypedDict):
    """모든 채팅 에이전트가 공유하는 기본 상태 필드.

    SocratesState, OracleState, LibrarianChatState는 이 TypedDict를 기반으로
    에이전트별 추가 필드를 정의한다.
    """

    # 입력 (에이전트 서비스가 초기화)
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    user_query: str
    turn_count: int
    source_context: dict | None
    explicit_mode: str | None
    agent_type: str  # 'socrates' | 'librarian' | 'oracle'

    # 제어
    next_step: str | None
    error: str | None
