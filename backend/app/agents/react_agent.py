"""ReAct 에이전트 생성 팩토리."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph


def build_react_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    system_prompt: str,
    max_steps: int = 8,
) -> CompiledStateGraph:
    """ReAct 에이전트 그래프를 생성한다.

    langchain.agents.create_agent (LangChain 1.0+)를 사용한다.
    langgraph.prebuilt.create_react_agent는 LangGraph v1.0에서 deprecated.

    Args:
        llm: tool calling을 지원하는 LLM
        tools: 에이전트가 사용할 tool 목록
        system_prompt: 에이전트 시스템 프롬프트
        max_steps: 최대 ReAct 루프 스텝 수. recursion_limit은 그래프 호출 시
            RunnableConfig(recursion_limit=max_steps * 2 + 1)로 전달해야 한다.

    Returns:
        컴파일된 LangGraph CompiledStateGraph
    """
    return create_agent(
        llm,
        tools=tools,
        system_prompt=system_prompt,
    )
