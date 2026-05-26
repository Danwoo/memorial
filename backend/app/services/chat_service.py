"""채팅 비즈니스 로직 (모든 agent_type의 채팅 세션을 다룬다).

책임:
- 세션 CRUD + 메시지 영속화
- 메시지 전송 흐름 조율 (AgentRegistry로 에이전트 선택 → StreamingStrategy 실행)
- 세션 메타데이터 갱신 (자동 제목, topic 태그, 세션 요약)
- 피드백/히스토리 조회

스트리밍 변환(SSE 와이어 포맷)은 _event_to_sse에서만 일어나고,
그래프 실행/이벤트 추출은 StreamingStrategy(ReactStreaming/DagStreaming)에 위임된다.

타입:
- Repository로부터 `ChatSession`/`ChatMessageRecord` 도메인 모델을 받아 사용한다.
- 외부(router)에는 도메인 모델 그대로 반환하고, router가 DTO로 매핑한다.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.base_context import AgentContext
from app.agents.container import get_agent_container
from app.agents.registry import AgentRegistry
from app.agents.streaming import StreamEvent, StreamingContext
from app.config.llm import get_analytical_llm
from app.domain.chat import ChatMessageRecord, ChatSession
from app.exceptions import LLMError
from app.repositories.protocols.chat_repository_protocol import ChatRepositoryProtocol

TITLE_GEN_PROMPT = (
    "다음 대화의 핵심 주제를 한국어 15자 이내 명사구로 요약하세요. "
    "설명 없이 제목만 출력하세요.\n\n"
    "사용자: {user_msg}\n"
    "AI: {ai_msg}"
)

SESSION_SUMMARY_PROMPT = (
    "다음 대화를 한국어 3줄 이내로 요약하세요. "
    "주요 주제, 핵심 인사이트, 결론을 포함하세요. "
    "설명 없이 요약만 출력하세요.\n\n{conversation}"
)

MAX_TITLE_LENGTH = 50
SESSION_SUMMARY_MAX_CHARS = 500
SESSION_SUMMARY_MSG_THRESHOLD = 4
CONVERSATION_PREVIEW_LENGTH = 2000
INITIAL_MESSAGE_COUNT_FOR_TITLE = 2  # 첫 user + 첫 AI 응답 직후

logger = logging.getLogger(__name__)


class ChatService:
    """채팅 비즈니스 로직 — 모든 agent_type의 세션을 다룬다.

    의존성: `ChatRepositoryProtocol` (의존성 역전 — 구현체는 모름)
    """

    def __init__(self, chat_repo: ChatRepositoryProtocol):
        self.chat_repo = chat_repo

    # ------------------------------------------------------------------
    # 세션 CRUD
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
        agent_type: str = "oracle",
    ) -> ChatSession:
        """새 채팅 세션 생성."""
        return await self.chat_repo.create_session(user_id, title, agent_type)

    async def get_session(self, session_id: UUID, user_id: UUID | None = None) -> ChatSession | None:
        """ID로 세션 조회. user_id 지정 시 소유권도 함께 검증."""
        return await self.chat_repo.get_session(session_id, user_id)

    async def list_sessions(self, user_id: UUID) -> list[ChatSession]:
        """사용자의 전체 세션 목록 조회 (최신순)."""
        sessions = await self.chat_repo.get_sessions_by_user(user_id)
        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    async def update_session_title(
        self, session_id: UUID, title: str, user_id: UUID | None = None
    ) -> bool:
        """세션 제목 수동 업데이트."""
        return await self.chat_repo.update_session_title(session_id, title, user_id)

    async def get_history(self, session_id: UUID) -> list[ChatMessageRecord]:
        """세션의 채팅 이력 조회 (DB 타임스탬프 포함)."""
        return await self.chat_repo.get_messages_raw(session_id)

    # ------------------------------------------------------------------
    # 피드백
    # ------------------------------------------------------------------

    async def add_feedback(
        self, session_id: UUID, message_index: int, user_id: UUID, rating: str
    ) -> bool:
        """메시지 피드백 저장."""
        return await self.chat_repo.add_feedback(session_id, message_index, user_id, rating)

    async def get_feedbacks(self, session_id: UUID) -> list[dict]:
        """세션의 전체 피드백 조회."""
        return await self.chat_repo.get_feedbacks(session_id)

    # ------------------------------------------------------------------
    # 메시지 전송 (핵심 흐름)
    # ------------------------------------------------------------------

    async def send_message(
        self,
        session_id: UUID,
        user_id: UUID,
        content: str,
        mode: str | None = None,
        source_context: dict | None = None,
        agent_type: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """메시지 전송 후 SSE 스트리밍으로 AI 응답 반환.

        AgentRegistry.get_entry()로 그래프와 스트리밍 전략을 함께 받아,
        전략이 흘려보내는 StreamEvent를 SSE 와이어 포맷으로 변환한다.
        """
        session = await self.chat_repo.get_session(session_id)
        if session is None:
            yield _sse({"error": "Session not found"})
            return

        effective_agent_type = agent_type or session.agent_type

        # 사용자 메시지 저장
        await self.chat_repo.add_message(session_id, HumanMessage(content=content))

        try:
            messages = await self.chat_repo.get_messages(session_id)
            turn_count = sum(1 for m in messages if isinstance(m, HumanMessage))

            entry = AgentRegistry.get_entry(effective_agent_type)
            if entry is None:
                yield _sse({"error": "No agent available"})
                return

            ctx = StreamingContext(
                messages=messages,
                user_query=content,
                user_id=str(user_id),
                session_id=str(session_id),
                turn_count=turn_count,
                mode=mode,
                source_context=source_context,
                agent_context=self._build_agent_context(),
            )

            full_response = ""
            async for event in entry.streaming.stream(entry.graph, ctx):
                if event.type == "content":
                    full_response += event.data.get("text", "")
                yield _event_to_sse(event)

            # 응답 저장
            if full_response:
                await self.chat_repo.add_message(session_id, AIMessage(content=full_response))

            # 메타데이터 후처리
            done_payload: dict = {"done": True}
            title = await self._maybe_generate_title(session_id, content, full_response)
            if title:
                done_payload["title"] = title

            if source_context and source_context.get("tags"):
                await self._save_topic_tags(session_id, source_context["tags"])

            yield _sse(done_payload)

        except asyncio.CancelledError:
            # SSE 클라이언트 연결 해제 — 정상 흐름, 리소스 누수 없이 종료
            logger.info("SSE client disconnected for session %s", session_id)
        except LLMError as e:
            # 알려진 LLM 실패 (parse/call) — 사용자에게 명확한 메시지
            logger.warning("LLM 실패로 응답 생성 불가 (session=%s): %s", session_id, e)
            yield _sse({"error": "AI 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요."})
        except Exception:
            # Boundary 레이어 fail-safe — 예상치 못한 시스템 예외는 일반화된 메시지로 graceful degradation.
            # 외부에 stack trace 노출하지 않고 logger.exception으로 보존만 한다.
            logger.exception("send_message 처리 중 예상치 못한 오류 (session=%s)", session_id)
            yield _sse({"error": "An internal error occurred"})

    # ------------------------------------------------------------------
    # 세션 요약
    # ------------------------------------------------------------------

    async def generate_session_summary(self, session_id: UUID) -> str | None:
        """세션의 대화를 LLM으로 요약하여 저장."""
        try:
            messages = await self.chat_repo.get_messages_raw(session_id)
            if len(messages) < SESSION_SUMMARY_MSG_THRESHOLD:
                return None

            conversation = "\n".join(
                f"{'사용자' if m.role == 'user' else 'AI'}: {m.content}" for m in messages
            )[:CONVERSATION_PREVIEW_LENGTH]

            llm = get_analytical_llm()
            prompt = SESSION_SUMMARY_PROMPT.format(conversation=conversation)
            result = await llm.ainvoke([SystemMessage(content=prompt)])
            summary = result.content.strip()[:SESSION_SUMMARY_MAX_CHARS]

            if summary:
                await self.chat_repo.update_session_summary(session_id, summary)
                return summary
        except Exception:
            logger.exception("세션 요약 생성 실패 (session_id=%s)", session_id)
        return None

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _build_agent_context(self) -> AgentContext:
        """DAG 파이프라인용 Runtime DI 컨텍스트 조립.

        ReactStreaming은 사용하지 않지만, 같은 StreamingContext를 공유하기 위해 항상 만든다.
        조립 비용이 낮아 매번 생성해도 무방하다.
        """
        container = get_agent_container()
        return AgentContext(
            hybrid_search=container.hybrid_search,
            vector_repo=container.vector_repo,
            diary_repo=container.diary_repo,
            chat_repo=self.chat_repo,
            community_summary=container.community_summary,
            graphrag_retrieval=container.graphrag_retrieval,
        )

    async def _save_topic_tags(self, session_id: UUID, tags: list[str]) -> None:
        """세션에 topic_tags 저장."""
        try:
            await self.chat_repo.update_session_topic_tags(session_id, tags)
        except Exception:
            logger.exception("topic_tags 저장 실패 (session_id=%s)", session_id)

    async def _maybe_generate_title(
        self, session_id: UUID, user_msg: str, ai_msg: str
    ) -> str | None:
        """첫 대화 완료 시 LLM으로 세션 제목 생성. 이미 제목이 있으면 스킵."""
        try:
            msg_count = await self.chat_repo.get_message_count(session_id)
            if msg_count != INITIAL_MESSAGE_COUNT_FOR_TITLE:
                return None

            llm = get_analytical_llm()
            prompt = TITLE_GEN_PROMPT.format(user_msg=user_msg[:200], ai_msg=ai_msg[:200])
            result = await llm.ainvoke([SystemMessage(content=prompt)])
            title = result.content.strip().strip('"').strip("'")[:MAX_TITLE_LENGTH]

            if title:
                await self.chat_repo.update_session_title(session_id, title)
                return title
        except Exception:
            logger.exception("세션 제목 자동 생성 실패 (session_id=%s)", session_id)

        return None


# ----------------------------------------------------------------------
# 모듈 레벨 헬퍼 — SSE 와이어 포맷팅
# ----------------------------------------------------------------------


def _sse(payload: dict) -> str:
    """dict → SSE 데이터 청크."""
    return f"data: {json.dumps(payload)}\n\n"


def _event_to_sse(event: StreamEvent) -> str:
    """StreamEvent → SSE 와이어 포맷.

    프론트엔드와 합의된 JSON 키마(content/step/references/error)를 유지한다.
    """
    if event.type == "content":
        return _sse({"content": event.data.get("text", "")})
    if event.type == "tool_start":
        return _sse({"step": event.data.get("name", ""), "status": "started"})
    if event.type == "tool_end":
        return _sse(
            {
                "step": event.data.get("name", ""),
                "status": "done",
                "detail": event.data.get("detail", ""),
            }
        )
    if event.type == "references":
        return _sse({"references": event.data.get("items", [])})
    if event.type == "error":
        return _sse({"error": event.data.get("message", "Unknown error")})
    # 미지의 이벤트는 그대로 흘려보냄
    return _sse(event.data)
