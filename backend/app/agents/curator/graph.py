"""Curator ReAct 에이전트 그래프."""

from __future__ import annotations


def build_curator_react_graph():
    """Curator ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.curator.prompts import CURATOR_REACT_SYSTEM_PROMPT
    from app.agents.react_agent import build_react_agent
    from app.agents.tools import CURATOR_TOOLS
    from app.config.llm import get_analytical_llm

    llm = get_analytical_llm()
    return build_react_agent(
        llm=llm,
        tools=CURATOR_TOOLS,
        system_prompt=CURATOR_REACT_SYSTEM_PROMPT,
    )


def register_curator_graph(registry) -> None:
    """Curator 에이전트를 레지스트리에 등록한다."""
    graph = build_curator_react_graph()
    registry.register("curator", graph)


# AgentRegistry 등록
def _register_curator():
    from app.agents.registry import AgentRegistry

    register_curator_graph(AgentRegistry)


_register_curator()
