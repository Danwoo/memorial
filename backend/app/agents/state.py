"""
Shared Agent State Schema for LangGraph
Based on Agent_Design_Spec.md - Section 1
"""
import operator
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    Global state shared across all agents in the LangGraph workflow.
    This is the "memory" that each node can read and write to.
    """

    # --- Context (대화 및 흐름) ---
    messages: Annotated[list[BaseMessage], operator.add]  # 대화 히스토리 (Append only)
    user_id: str
    context: dict | None  # 추가 컨텍스트 (mode, user preferences 등)

    # --- Input Data (처리 대상) ---
    target_memory_id: str | None   # 분석 대상 메모리 ID (for Librarian)
    target_text: str | None        # 분석 대상 본문 텍스트
    source_url: str | None         # 원본 URL (Scraper가 추출한 경우)

    # --- Working Memory (작업 공간) ---
    # Curator가 분석한 결과
    classification: Literal["INSIGHT", "FACT", "SPAM"] | None
    summary: str | None            # 한 줄 요약
    tags: list[str] | None         # 태그 목록

    # Ontologist가 추출한 결과
    extracted_entities: list[dict] | None  # Node 후보군 [{"name": "React", "type": "Concept"}, ...]
    extracted_relations: list[dict] | None # Edge 후보군 [{"source": "A", "target": "B", "type": "USES"}, ...]

    # --- Flags & Control ---
    is_streaming: bool                # 현재 프론트엔드로 스트리밍 중인지 여부
    next_step: str | None          # 다음 실행할 노드 (Router가 결정)
    error: str | None              # 에러 메시지 (있으면 중단)
