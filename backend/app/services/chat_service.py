import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.socrates.nodes.chat import prepare_socrates_context
from app.config.llm import get_analytical_llm, get_streaming_llm
from app.repositories.chat_repository import ChatRepository

TITLE_GEN_PROMPT = (
    "다음 대화의 핵심 주제를 한국어 15자 이내 명사구로 요약하세요. "
    "설명 없이 제목만 출력하세요.\n\n"
    "사용자: {user_msg}\n"
    "AI: {ai_msg}"
)

MAX_TITLE_LENGTH = 50

logger = logging.getLogger(__name__)


class ChatService:
    """채팅 및 소크라테스 대화 비즈니스 로직."""

    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
    ) -> dict:
        """새 채팅 세션 생성."""
        return await self.chat_repo.create_session(user_id, title)

    async def get_session(self, session_id: UUID) -> dict | None:
        """ID로 세션 조회."""
        return await self.chat_repo.get_session(session_id)

    async def list_sessions(self, user_id: UUID) -> list[dict]:
        """사용자의 전체 세션 목록 조회 (최신순)."""
        sessions = await self.chat_repo.get_sessions_by_user(user_id)
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)

    async def send_message(
        self,
        session_id: UUID,
        user_id: UUID,
        content: str,
        mode: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """메시지 전송 후 실시간 SSE 스트리밍으로 AI 응답 반환.

        RAG 컨텍스트 준비 후 llm.astream()으로 토큰 단위 스트리밍.
        """
        session = await self.chat_repo.get_session(session_id)
        if not session:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        # 사용자 메시지 저장
        user_message = HumanMessage(content=content)
        await self.chat_repo.add_message(session_id, user_message)

        try:
            # 대화 이력 조회
            messages = await self.chat_repo.get_messages(session_id)

            # RAG 검색, 저널, 모드별 프롬프트 준비
            lc_messages = await prepare_socrates_context(messages, mode, user_id=str(user_id))

            # LLM에서 토큰 단위 스트리밍
            llm = get_streaming_llm()
            full_response = ""

            async for chunk in llm.astream(lc_messages):
                chunk_text = chunk.content
                if chunk_text:
                    full_response += chunk_text
                    yield f"data: {json.dumps({'content': chunk_text})}\n\n"

            # 완성된 응답 저장
            if full_response:
                await self.chat_repo.add_message(session_id, AIMessage(content=full_response))

            # 첫 대화 완료 시 세션 제목 자동 생성
            title = await self._maybe_generate_title(session_id, content, full_response)
            done_data: dict = {"done": True}
            if title:
                done_data["title"] = title

            yield f"data: {json.dumps(done_data)}\n\n"

        except asyncio.CancelledError:
            logger.info("SSE client disconnected for session %s", session_id)
        except Exception:
            logger.exception("Error during SSE streaming for session %s", session_id)
            yield f"data: {json.dumps({'error': 'An internal error occurred'})}\n\n"

    async def update_session_title(self, session_id: UUID, title: str) -> bool:
        """세션 제목 수동 업데이트."""
        return await self.chat_repo.update_session_title(session_id, title)

    async def get_history(self, session_id: UUID) -> list[dict]:
        """세션의 채팅 이력 조회 (DB 타임스탬프 포함)."""
        return await self.chat_repo.get_messages_raw(session_id)

    async def _maybe_generate_title(self, session_id: UUID, user_msg: str, ai_msg: str) -> str | None:
        """첫 대화 완료 시 LLM으로 세션 제목 생성. 이미 제목이 있으면 스킵."""
        try:
            msg_count = await self.chat_repo.get_message_count(session_id)
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
                await self.chat_repo.update_session_title(session_id, title)
                return title
        except Exception:
            logger.exception("세션 제목 자동 생성 실패 (session_id=%s)", session_id)

        return None
