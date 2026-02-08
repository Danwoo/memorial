"""
Chat Service
Business logic for chat and Socratic dialogue.
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.socrates import socrates_graph
from app.agents.state import AgentState
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
        Send a message and get AI response via SSE streaming.
        Yields SSE-formatted strings (``data: {...}\\n\\n``).

        NOTE: Current implementation uses simulated streaming -- the full
        LLM response is obtained first, then split into chunks. Real
        token-level streaming will be implemented in Phase 3.
        """
        session = await self.chat_repo.get_session(session_id)
        if not session:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return

        # Persist user message
        user_msg = HumanMessage(content=content)
        await self.chat_repo.add_message(session_id, user_msg)

        try:
            # Retrieve conversation history
            messages = await self.chat_repo.get_messages(session_id)

            # Build initial state for the Socrates agent
            initial_state: AgentState = {
                "messages": messages,
                "user_id": str(user_id),
                "context": {"mode": mode} if mode else {},
                "target_memory_id": None,
                "target_text": None,
                "classification": None,
                "summary": None,
                "tags": None,
                "extracted_entities": None,
                "extracted_relations": None,
                "is_streaming": True,
                "next_step": None,
                "error": None,
            }

            # Run the Socrates LangGraph
            result = await socrates_graph.ainvoke(initial_state)

            # Extract AI response
            new_messages = result.get("messages", [])
            if new_messages:
                ai_msg = new_messages[-1]
                ai_content = ai_msg.content if hasattr(ai_msg, "content") else str(ai_msg)

                # Persist assistant message
                await self.chat_repo.add_message(session_id, AIMessage(content=ai_content))

                # Stream in chunks (simulated streaming)
                chunk_size = 50
                for i in range(0, len(ai_content), chunk_size):
                    chunk = ai_content[i : i + chunk_size]
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'done': True})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected -- clean up gracefully
            logger.info("SSE client disconnected for session %s", session_id)
        except Exception:
            logger.exception("Error during SSE streaming for session %s", session_id)
            yield f"data: {json.dumps({'error': 'An internal error occurred'})}\n\n"

    async def get_history(self, session_id: UUID) -> list[dict]:
        """Get chat history for a session."""
        messages = await self.chat_repo.get_messages(session_id)

        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                result.append({
                    "role": "user",
                    "content": msg.content,
                    "created_at": datetime.now().isoformat(),
                })
            elif isinstance(msg, AIMessage):
                result.append({
                    "role": "assistant",
                    "content": msg.content,
                    "created_at": datetime.now().isoformat(),
                })

        return result
