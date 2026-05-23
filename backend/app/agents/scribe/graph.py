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


def _register_scribe():
    from app.agents.registry import AgentRegistry
    from app.agents.streaming import ReactStreaming

    graph = build_scribe_react_graph()
    AgentRegistry.register("scribe", graph=graph, streaming=ReactStreaming())
