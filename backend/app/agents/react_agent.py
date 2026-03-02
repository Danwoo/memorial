"""ReAct 에이전트 생성 팩토리."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent


def build_react_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    max_steps: int = 8,
) -> CompiledStateGraph:
    """ReAct 에이전트 그래프를 생성한다.

    Args:
        llm: tool calling을 지원하는 LLM
        tools: 에이전트가 사용할 tool 목록
        system_prompt: 에이전트 시스템 프롬프트
        max_steps: 최대 ReAct 루프 스텝 수 — invoke 시 recursion_limit으로 전달 (기본 8)

    Returns:
        컴파일된 LangGraph CompiledStateGraph
    """
    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )
