"""그래프 실행 → 도메인 이벤트 변환을 담당하는 Streaming Strategy.

LangGraph 그래프 실행 결과를 순수 도메인 객체(StreamEvent)로 변환한다.
SSE/WebSocket 같은 전송 계층 포맷팅은 호출자(ChatService)가 담당한다.

이 분리 덕분에:
- Strategy는 순수 도메인 로직만 갖고 단위 테스트가 가능하다
- 다른 전송 계층 추가 시 Strategy는 변경되지 않는다
- agent_type → Strategy 매핑은 AgentRegistry에 집중되어 매직 셋이 사라진다
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


StreamEventType = Literal[
    "content",
    "tool_start",
    "tool_end",
    "references",
    "error",
]


@dataclass(frozen=True)
class StreamEvent:
    """그래프 실행 중 발생하는 도메인 이벤트.

    전송 계층(SSE/WebSocket)이 직접 사용할 수 있는 불변 데이터 객체.
    """

    type: StreamEventType
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StreamingContext:
    """Streaming 실행에 필요한 입력 묶음."""

    messages: list
    user_query: str
    user_id: str
    session_id: str
    turn_count: int = 0
    mode: str | None = None
    source_context: dict | None = None
    agent_context: Any = None  # DAG용 Runtime DI 컨텍스트


@dataclass
class StreamResult:
    """스트림 종료 후 누적된 결과 (AI 응답 텍스트 등)."""

    text: str = ""


class StreamingStrategy(Protocol):
    """그래프 실행 → StreamEvent 변환 전략 인터페이스."""

    async def stream(
        self,
        graph: Any,
        ctx: StreamingContext,
    ) -> AsyncIterator[StreamEvent]:
        """그래프를 실행하면서 StreamEvent들을 yield한다."""
        ...


class ReactStreaming:
    """ReAct 에이전트 스트리밍 — `astream_events v2` 기반.

    LangChain의 표준 ReAct API가 흘려보내는 이벤트들을
    프로젝트의 StreamEvent 타입으로 변환한다.
    """

    async def stream(
        self,
        graph: Any,
        ctx: StreamingContext,
    ) -> AsyncIterator[StreamEvent]:
        initial_state = {"messages": ctx.messages}
        run_config = RunnableConfig(
            configurable={
                "user_id": ctx.user_id,
                "session_id": ctx.session_id,
            }
        )

        try:
            async for event in graph.astream_events(initial_state, config=run_config, version="v2"):
                event_type = event.get("event", "")

                if event_type == "on_chat_model_stream":
                    async for token in _extract_chat_tokens(event):
                        yield StreamEvent(type="content", data={"text": token})

                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name:
                        yield StreamEvent(type="tool_start", data={"name": tool_name})

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "")
                    if not tool_name:
                        continue
                    output = event.get("data", {}).get("output", "")
                    detail = str(output)[:200] if output else ""
                    yield StreamEvent(type="tool_end", data={"name": tool_name, "detail": detail})

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("ReactStreaming 실행 중 오류")
            yield StreamEvent(type="error", data={"message": str(e)})


class DagStreaming:
    """DAG 파이프라인 스트리밍.

    파이프라인을 `ainvoke`로 동기 실행하여 `llm_messages`를 얻고,
    그 메시지를 streaming LLM에 다시 보내 토큰을 흘려보낸다.

    참고: 파이프라인은 retrieval/grading/enrichment 등을 거치지만 최종 응답은
    별도 streaming LLM에서 생성되는 구조라 두 단계로 나뉜다.
    """

    def __init__(
        self,
        state_builder: Callable[..., dict],
        llm_factory: Callable[[], Any],
    ):
        """
        Args:
            state_builder: agent_type별 초기 상태 빌더 (build_oracle_initial_state 등)
            llm_factory: streaming LLM 인스턴스 팩토리 (DI for testability)
        """
        self._state_builder = state_builder
        self._llm_factory = llm_factory

    async def stream(
        self,
        graph: Any,
        ctx: StreamingContext,
    ) -> AsyncIterator[StreamEvent]:
        initial_state = self._state_builder(
            messages=ctx.messages,
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            user_query=ctx.user_query,
            turn_count=ctx.turn_count,
            mode=ctx.mode,
            source_context=ctx.source_context,
        )

        try:
            if ctx.agent_context is not None:
                result = await graph.ainvoke(initial_state, context=ctx.agent_context)
            else:
                result = await graph.ainvoke(initial_state)

            if result.get("error"):
                logger.warning("DAG 파이프라인 경고: %s", result["error"])

            llm_messages = result.get("llm_messages")
            if not llm_messages:
                logger.error("DAG 파이프라인 llm_messages 누락")
                yield StreamEvent(type="error", data={"message": "응답 생성에 실패했습니다"})
                return

            llm = self._llm_factory()
            async for chunk in llm.astream(llm_messages):
                text = chunk.content
                if text:
                    yield StreamEvent(type="content", data={"text": text})

            references = result.get("references", [])
            if references:
                yield StreamEvent(type="references", data={"items": references})

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("DagStreaming 실행 중 오류")
            yield StreamEvent(type="error", data={"message": str(e)})


async def _extract_chat_tokens(event: dict) -> AsyncIterator[str]:
    """`on_chat_model_stream` 이벤트에서 텍스트 토큰을 추출한다.

    LangChain은 content를 str 또는 list[dict] 두 형태로 흘려보낸다.
    """
    chunk = event.get("data", {}).get("chunk")
    if chunk is None or not hasattr(chunk, "content"):
        return
    content = chunk.content
    if isinstance(content, str):
        if content:
            yield content
        return
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if text:
                    yield text
