import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import app.agents.librarian.graph  # noqa: F401

# 에이전트 그래프 초기화 (import 시 registry 등록)
import app.agents.oracle.graph  # noqa: F401
import app.agents.socrates.graph  # noqa: F401
from app.agents.base_context import AgentContext
from app.agents.container import get_agent_container
from app.agents.librarian.state import build_librarian_chat_initial_state
from app.agents.oracle.state import build_oracle_initial_state
from app.agents.registry import AgentRegistry
from app.agents.socrates.state import build_socrates_initial_state
from app.config.llm import get_analytical_llm, get_streaming_llm
from app.repositories.socrates_repository import SocratesRepository

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
SESSION_SUMMARY_MSG_THRESHOLD = 4
CONVERSATION_PREVIEW_LENGTH = 2000

logger = logging.getLogger(__name__)


class SocratesService:
    """소크라테스 대화 비즈니스 로직."""

    def __init__(self, socrates_repo: SocratesRepository):
        self.socrates_repo = socrates_repo

    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
        agent_type: str = "oracle",
    ) -> dict:
        """새 채팅 세션 생성."""
        return await self.socrates_repo.create_session(user_id, title, agent_type)

    async def get_session(self, session_id: UUID, user_id: UUID | None = None) -> dict | None:
        """ID로 세션 조회. user_id 지정 시 소유권도 함께 검증."""
        return await self.socrates_repo.get_session(session_id, user_id)

    async def list_sessions(self, user_id: UUID) -> list[dict]:
        """사용자의 전체 세션 목록 조회 (최신순)."""
        sessions = await self.socrates_repo.get_sessions_by_user(user_id)
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)

    async def send_message(
        self,
        session_id: UUID,
        user_id: UUID,
        content: str,
        mode: str | None = None,
        source_context: dict | None = None,
        agent_type: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """메시지 전송 후 실시간 SSE 스트리밍으로 AI 응답 반환.

        AgentRegistry에서 agent_type 기반으로 적절한 그래프를 선택하여 실행한다.
        agent_type이 None이면 세션에 저장된 agent_type을 사용한다.
        """
        session = await self.socrates_repo.get_session(session_id)
        if not session:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        # agent_type 결정: 요청값 > 세션값 > 기본값(oracle)
        effective_agent_type = agent_type or session.get("agent_type", "oracle")

        # 사용자 메시지 저장
        user_message = HumanMessage(content=content)
        await self.socrates_repo.add_message(session_id, user_message)

        try:
            # 대화 이력 조회
            messages = await self.socrates_repo.get_messages(session_id)

            # 턴 수 계산 (HumanMessage 개수 기준)
            turn_count = sum(1 for m in messages if isinstance(m, HumanMessage))

            # Runtime DI 컨텍스트 조립 (AgentContext 공유)
            container = get_agent_container()
            ctx = AgentContext(
                hybrid_search=container.hybrid_search,
                vector_repo=container.vector_repo,
                diary_repo=container.diary_repo,
                socrates_repo=self.socrates_repo,
                community_summary=container.community_summary,
            )

            # agent_type별 초기 상태 빌더 선택
            _STATE_BUILDERS = {
                "socrates": build_socrates_initial_state,
                "oracle": build_oracle_initial_state,
                "librarian": build_librarian_chat_initial_state,
            }
            state_builder = _STATE_BUILDERS.get(effective_agent_type, build_oracle_initial_state)

            # 초기 상태 구성
            initial_state = state_builder(
                messages=messages,
                user_id=str(user_id),
                session_id=str(session_id),
                user_query=content,
                turn_count=turn_count,
                mode=mode,
                source_context=source_context,
            )

            # AgentRegistry에서 agent_type 기반 그래프 선택
            graph = AgentRegistry.get(effective_agent_type)
            if graph is None:
                logger.warning("agent_type=%s에 해당하는 그래프 없음, oracle 폴백", effective_agent_type)
                from app.agents.oracle.graph import oracle_graph

                graph = oracle_graph

            # LangGraph 파이프라인 실행 (context= 파라미터로 Runtime DI 주입)
            result = await graph.ainvoke(initial_state, context=ctx)

            if result.get("error"):
                logger.warning("파이프라인 경고 (session=%s): %s", session_id, result["error"])

            llm_messages = result.get("llm_messages")
            if not llm_messages:
                logger.error("파이프라인 llm_messages 누락 (session=%s)", session_id)
                yield f"data: {json.dumps({'error': '응답 생성에 실패했습니다'})}\n\n"
                return

            references = result.get("references", [])

            # LLM에서 토큰 단위 스트리밍
            llm = get_streaming_llm()
            full_response = ""

            async for chunk in llm.astream(llm_messages):
                chunk_text = chunk.content
                if chunk_text:
                    full_response += chunk_text
                    yield f"data: {json.dumps({'content': chunk_text})}\n\n"

            # 완성된 응답 저장
            if full_response:
                await self.socrates_repo.add_message(session_id, AIMessage(content=full_response))

            # 참조 메모리 이벤트
            if references:
                yield f"data: {json.dumps({'references': references})}\n\n"

            # 첫 대화 완료 시 세션 제목 자동 생성
            title = await self._maybe_generate_title(session_id, content, full_response)
            done_data: dict = {"done": True}
            if title:
                done_data["title"] = title

            # source_context 태그가 있으면 세션에 저장
            if source_context and source_context.get("tags"):
                await self._save_topic_tags(session_id, source_context["tags"])

            yield f"data: {json.dumps(done_data)}\n\n"

        except asyncio.CancelledError:
            logger.info("SSE client disconnected for session %s", session_id)
        except Exception:
            logger.exception("Error during SSE streaming for session %s", session_id)
            yield f"data: {json.dumps({'error': 'An internal error occurred'})}\n\n"

    async def update_session_title(self, session_id: UUID, title: str) -> bool:
        """세션 제목 수동 업데이트."""
        return await self.socrates_repo.update_session_title(session_id, title)

    async def get_history(self, session_id: UUID) -> list[dict]:
        """세션의 채팅 이력 조회 (DB 타임스탬프 포함)."""
        return await self.socrates_repo.get_messages_raw(session_id)

    async def add_feedback(self, session_id: UUID, message_index: int, user_id: UUID, rating: str) -> bool:
        """메시지 피드백 저장."""
        return await self.socrates_repo.add_feedback(session_id, message_index, user_id, rating)

    async def get_feedbacks(self, session_id: UUID) -> list[dict]:
        """세션의 전체 피드백 조회."""
        return await self.socrates_repo.get_feedbacks(session_id)

    async def generate_session_summary(self, session_id: UUID) -> str | None:
        """세션의 대화를 LLM으로 요약하여 저장."""
        try:
            messages = await self.socrates_repo.get_messages_raw(session_id)
            if len(messages) < SESSION_SUMMARY_MSG_THRESHOLD:
                return None

            conversation = "\n".join(f"{'사용자' if m['role'] == 'user' else 'AI'}: {m['content']}" for m in messages)[
                :CONVERSATION_PREVIEW_LENGTH
            ]

            llm = get_analytical_llm()
            prompt = SESSION_SUMMARY_PROMPT.format(conversation=conversation)
            result = await llm.ainvoke([SystemMessage(content=prompt)])
            summary = result.content.strip()[:500]

            if summary:
                await self.socrates_repo.update_session_summary(session_id, summary)
                return summary
        except Exception:
            logger.exception("세션 요약 생성 실패 (session_id=%s)", session_id)
        return None

    async def _save_topic_tags(self, session_id: UUID, tags: list[str]) -> None:
        """세션에 topic_tags 저장."""
        try:
            await self.socrates_repo.update_session_topic_tags(session_id, tags)
        except Exception:
            logger.exception("topic_tags 저장 실패 (session_id=%s)", session_id)

    async def _maybe_generate_title(self, session_id: UUID, user_msg: str, ai_msg: str) -> str | None:
        """첫 대화 완료 시 LLM으로 세션 제목 생성. 이미 제목이 있으면 스킵."""
        try:
            msg_count = await self.socrates_repo.get_message_count(session_id)
            if msg_count != 2:
                return None

            llm = get_analytical_llm()
            prompt = TITLE_GEN_PROMPT.format(
                user_msg=user_msg[:200],
                ai_msg=ai_msg[:200],
            )
            result = await llm.ainvoke([SystemMessage(content=prompt)])
            title = result.content.strip().strip('"').strip("'")[:MAX_TITLE_LENGTH]

            if title:
                await self.socrates_repo.update_session_title(session_id, title)
                return title
        except Exception:
            logger.exception("세션 제목 자동 생성 실패 (session_id=%s)", session_id)

        return None
