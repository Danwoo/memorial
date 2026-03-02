"""Supervisor 라우팅 에이전트."""

from __future__ import annotations

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.agents.supervisor.prompts import SUPERVISOR_SYSTEM_PROMPT


@tool
def route_to_socrates(reason: str) -> str:
    """감성 코칭 에이전트(Socrates)로 라우팅합니다. reason에 라우팅 이유를 설명하세요."""
    return f"ROUTE:socrates:{reason}"


@tool
def route_to_librarian(reason: str) -> str:
    """지식 검색 에이전트(Librarian)로 라우팅합니다. reason에 라우팅 이유를 설명하세요."""
    return f"ROUTE:librarian:{reason}"


@tool
def route_to_analyst(reason: str) -> str:
    """패턴 분석 에이전트(Analyst)로 라우팅합니다. reason에 라우팅 이유를 설명하세요."""
    return f"ROUTE:analyst:{reason}"


@tool
def respond_directly(response: str) -> str:
    """직접 응답합니다 (단순 인사/잡담). response에 응답 내용을 작성하세요."""
    return f"DIRECT:{response}"


SUPERVISOR_TOOLS = [
    route_to_socrates,
    route_to_librarian,
    route_to_analyst,
    respond_directly,
]


def build_supervisor_graph():
    """Supervisor 에이전트 그래프를 빌드한다."""
    from app.config.llm import get_analytical_llm

    llm = get_analytical_llm()
    return create_react_agent(
        model=llm,
        tools=SUPERVISOR_TOOLS,
        prompt=SUPERVISOR_SYSTEM_PROMPT,
    )


def parse_supervisor_result(result: dict) -> tuple[str, str]:
    """Supervisor 결과에서 (target_agent, reason) 쌍을 추출한다."""
    messages = result.get("messages", [])
    for msg in reversed(messages):
        content = getattr(msg, "content", "") or ""
        if isinstance(content, str):
            if content.startswith("ROUTE:"):
                parts = content.split(":", 2)
                if len(parts) >= 3:
                    return parts[1], parts[2]
            elif content.startswith("DIRECT:"):
                return "direct", content[7:]
    return "socrates", "기본 라우팅"


def register_supervisor_graph(registry) -> None:
    """Supervisor 에이전트를 레지스트리에 등록한다."""
    graph = build_supervisor_graph()
    registry.register("supervisor", graph)


# AgentRegistry 등록
def _register_supervisor():
    from app.agents.registry import AgentRegistry

    register_supervisor_graph(AgentRegistry)


_register_supervisor()
