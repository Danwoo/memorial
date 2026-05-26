"""에이전트 등록소.

각 에이전트는 컴파일된 그래프 + 스트리밍 전략을 함께 등록한다.
ChatService는 `get_entry(agent_type)`으로 두 가지를 한 번에 받아 사용하므로,
`REACT_AGENT_TYPES` 같은 매직 셋이 필요 없다.

backward-compat:
    `get(agent_type)`은 그래프만 반환하는 기존 시그니처를 유지한다.
    신규 코드는 `get_entry(agent_type)`을 사용해 streaming 전략까지 받는다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import ClassVar

from app.agents.streaming import StreamingStrategy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentEntry:
    """에이전트의 실행에 필요한 capability 묶음.

    Attributes:
        graph: 컴파일된 LangGraph (DAG 또는 ReAct)
        streaming: 그래프 실행 결과를 StreamEvent로 변환하는 전략
    """

    graph: object
    streaming: StreamingStrategy


class AgentRegistry:
    """에이전트 등록소 — agent_type 문자열로 AgentEntry를 반환."""

    _entries: ClassVar[dict[str, AgentEntry]] = {}
    _fallback_agent_type: ClassVar[str] = "socrates"

    @classmethod
    def register(
        cls,
        agent_type: str,
        graph: object,
        streaming: StreamingStrategy,
    ) -> None:
        """에이전트를 등록한다.

        Args:
            agent_type: 에이전트 식별자 (예: "socrates", "oracle")
            graph: 컴파일된 LangGraph
            streaming: 이 에이전트의 그래프 결과를 변환하는 스트리밍 전략
        """
        cls._entries[agent_type] = AgentEntry(graph=graph, streaming=streaming)
        logger.debug("에이전트 등록됨: %s", agent_type)

    @classmethod
    def get_entry(cls, agent_type: str) -> AgentEntry | None:
        """agent_type으로 등록된 AgentEntry 반환. 없으면 fallback으로 폴백."""
        if agent_type in cls._entries:
            return cls._entries[agent_type]
        logger.warning("미등록 agent_type=%s, %s로 폴백", agent_type, cls._fallback_agent_type)
        return cls._entries.get(cls._fallback_agent_type)

    @classmethod
    def get(cls, agent_type: str) -> object | None:
        """[하위호환] agent_type으로 등록된 그래프만 반환.

        신규 코드는 `get_entry`를 사용한다.
        """
        entry = cls.get_entry(agent_type)
        return entry.graph if entry else None

    @classmethod
    def available(cls) -> list[str]:
        """등록된 agent_type 목록 반환."""
        return list(cls._entries.keys())

    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """agent_type이 등록되어 있는지 확인."""
        return agent_type in cls._entries

    @classmethod
    def clear(cls) -> None:
        """테스트용 — 등록된 모든 에이전트 제거."""
        cls._entries.clear()
