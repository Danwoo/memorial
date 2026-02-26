import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """LangGraph 워크플로우 전체에서 공유되는 글로벌 에이전트 상태."""

    # --- 컨텍스트 (대화 및 흐름) ---
    messages: Annotated[list[BaseMessage], operator.add]  # 대화 히스토리 (Append only)
    user_id: str
    context: dict | None  # 추가 컨텍스트 (mode, user preferences 등)

    # --- 입력 데이터 (처리 대상) ---
    target_scrap_id: str | None  # 분석 대상 스크랩 ID (Librarian용)
    target_text: str | None  # 분석 대상 본문 텍스트
    source_url: str | None  # 원본 URL

    # --- 작업 공간 (Curator 분석 결과) ---
    classification: Literal["INSIGHT", "FACT", "SPAM"] | None
    summary: str | None  # 한 줄 요약
    tags: list[str] | None  # 태그 목록

    # --- 작업 공간 (Ontologist 추출 결과) ---
    extracted_entities: list[dict] | None  # 노드 후보군
    extracted_relations: list[dict] | None  # 엣지 후보군

    # --- 플래그 및 제어 ---
    is_streaming: bool  # 프론트엔드 스트리밍 여부
    next_step: str | None  # 다음 실행 노드 (Router 결정)
    error: str | None  # 에러 메시지 (존재 시 중단)


def build_librarian_initial_state(
    scrap_id: str,
    content: str,
    user_id: str,
) -> AgentState:
    """Librarian 그래프 실행을 위한 초기 상태 생성.

    Args:
        scrap_id: 처리 대상 스크랩 ID
        content: 분석 대상 본문 텍스트
        user_id: 소유 사용자 ID
    """
    return {
        "messages": [],
        "user_id": user_id,
        "context": {},
        "target_scrap_id": scrap_id,
        "target_text": content,
        "classification": None,
        "summary": None,
        "tags": None,
        "extracted_entities": None,
        "extracted_relations": None,
        "is_streaming": False,
        "next_step": None,
        "error": None,
    }
