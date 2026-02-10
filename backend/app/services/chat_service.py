"""
Chat Service
Business logic for chat and Socratic dialogue.

Real-time token streaming: bypasses the LangGraph ``ainvoke`` path and
calls ``llm.astream()`` directly so that each token is yielded to the
client as an SSE event immediately.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.socrates.nodes.chat import prepare_socrates_context
from app.config.llm import get_streaming_llm
from app.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat business logic."""

    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
    ) -> dict:
        """Create a new chat session."""
        return await self.chat_repo.create_session(user_id, title)

    async def get_session(self, session_id: UUID) -> dict | None:
        """Get a session by ID."""
        return await self.chat_repo.get_session(session_id)

    async def list_sessions(self, user_id: UUID) -> list[dict]:
        """List all sessions for a user."""
        sessions = await self.chat_repo.get_sessions_by_user(user_id)
        return sorted(sessions, key=lambda x: x["created_at"], reverse=True)

    async def send_message(
        self,
        session_id: UUID,
        user_id: UUID,
        content: str,
        mode: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and get AI response via real-time SSE streaming.

        Bypasses the LangGraph ``ainvoke`` path: context preparation (RAG,
        journal, mode prompts) is done first, then ``llm.astream()`` yields
        tokens one-by-one directly to the client.
        """
        session = await self.chat_repo.get_session(session_id)
        if not session:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        # Persist user message
        user_message = HumanMessage(content=content)
        await self.chat_repo.add_message(session_id, user_message)

        try:
            # Retrieve conversation history
            messages = await self.chat_repo.get_messages(session_id)

            # Prepare context: RAG search, journal, mode prompts
            lc_messages = await prepare_socrates_context(messages, mode, user_id=str(user_id))

            # Stream tokens directly from LLM
            llm = get_streaming_llm()
            full_response = ""

            async for chunk in llm.astream(lc_messages):
                chunk_text = chunk.content
                if chunk_text:
                    full_response += chunk_text
                    yield f"data: {json.dumps({'content': chunk_text})}\n\n"

            # Persist complete response
            if full_response:
                await self.chat_repo.add_message(session_id, AIMessage(content=full_response))

            yield f"data: {json.dumps({'done': True})}\n\n"

        except asyncio.CancelledError:
            logger.info("SSE client disconnected for session %s", session_id)
        except Exception:
            logger.exception("Error during SSE streaming for session %s", session_id)
            yield f"data: {json.dumps({'error': 'An internal error occurred'})}\n\n"

    async def get_history(self, session_id: UUID) -> list[dict]:
        """Get chat history for a session with actual DB timestamps."""
        return await self.chat_repo.get_messages_raw(session_id)
