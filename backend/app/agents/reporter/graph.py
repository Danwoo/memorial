"""Reporter ReAct 에이전트 그래프."""

from __future__ import annotations


def build_reporter_react_graph():
    """Reporter ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.react_agent import build_react_agent
    from app.agents.reporter.prompts import REPORTER_REACT_SYSTEM_PROMPT
    from app.agents.tools import REPORTER_TOOLS
    from app.config.llm import get_analytical_llm

    llm = get_analytical_llm()
    return build_react_agent(
        llm=llm,
        tools=REPORTER_TOOLS,
        system_prompt=REPORTER_REACT_SYSTEM_PROMPT,
    )


def _register_reporter():
    from app.agents.registry import AgentRegistry
    from app.agents.streaming import ReactStreaming

    graph = build_reporter_react_graph()
    AgentRegistry.register("reporter", graph=graph, streaming=ReactStreaming())
