"""Scribe ReAct 에이전트 그래프."""

from __future__ import annotations


def build_scribe_react_graph():
    """Scribe ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.react_agent import build_react_agent
    from app.agents.scribe.prompts import SCRIBE_REACT_SYSTEM_PROMPT
    from app.agents.tools import SCRIBE_TOOLS
    from app.config.llm import get_analytical_llm

    llm = get_analytical_llm()
    return build_react_agent(
        llm=llm,
        tools=SCRIBE_TOOLS,
        system_prompt=SCRIBE_REACT_SYSTEM_PROMPT,
    )


def register_scribe_graph(registry) -> None:
    """Scribe 에이전트를 레지스트리에 등록한다."""
    graph = build_scribe_react_graph()
    registry.register("scribe", graph)


# AgentRegistry 등록 (fallback import 방식에서 호출)
def _register_scribe():
    from app.agents.registry import AgentRegistry

    register_scribe_graph(AgentRegistry)
