"""Analyst ReAct 에이전트 그래프."""

from __future__ import annotations


def build_analyst_react_graph():
    """Analyst ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.analyst.prompts import ANALYST_REACT_SYSTEM_PROMPT
    from app.agents.react_agent import build_react_agent
    from app.agents.tools import ANALYST_TOOLS
    from app.config.llm import get_analytical_llm

    llm = get_analytical_llm()
    return build_react_agent(
        llm=llm,
        tools=ANALYST_TOOLS,
        system_prompt=ANALYST_REACT_SYSTEM_PROMPT,
    )


def build_analyst_initial_state(query: str, context: str = "", config=None) -> dict:
    """Analyst 초기 상태를 생성한다."""
    from langchain_core.messages import HumanMessage

    content = f"{context}\n\n{query}" if context else query
    return {"messages": [HumanMessage(content=content)]}


def register_analyst_graph(registry) -> None:
    """Analyst 에이전트를 레지스트리에 등록한다."""
    graph = build_analyst_react_graph()
    registry.register("analyst", graph)
