"""
Chat Repository
Data access layer for chat sessions - Supabase implementation.

All public methods are async and delegate synchronous Supabase calls
to a thread via ``asyncio.to_thread`` so that the event loop is never blocked.
"""
import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from supabase import Client

logger = logging.getLogger(__name__)


class ChatRepository:
    """Repository for chat session operations with Supabase persistence."""

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
    ) -> dict:
        """Create a new chat session in Supabase."""
        title = title or f"Chat {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"

        data = {"user_id": str(user_id), "title": title}

        result = await asyncio.to_thread(self._insert_session, data)

        if result.data:
            session = result.data[0]
            return {
                "id": session["id"],
                "user_id": session["user_id"],
                "title": session["title"],
                "created_at": session["created_at"],
            }

        # Fallback - should not happen
        session_id = str(uuid4())
        return {
            "id": session_id,
            "user_id": str(user_id),
            "title": title,
            "created_at": datetime.now(UTC).isoformat(),
        }

    async def get_session(self, session_id: UUID) -> dict | None:
        """Get a session by ID from Supabase."""
        result = await asyncio.to_thread(self._select_session, str(session_id))

        if result.data and len(result.data) > 0:
            session = result.data[0]
            return {
                "id": session["id"],
                "user_id": session["user_id"],
                "title": session["title"],
                "created_at": session["created_at"],
            }
        return None

    async def get_sessions_by_user(self, user_id: UUID) -> list[dict]:
        """Get all sessions for a user from Supabase."""
        result = await asyncio.to_thread(self._select_sessions_by_user, str(user_id))

        return [
            {
                "id": s["id"],
                "user_id": s["user_id"],
                "title": s["title"],
                "created_at": s["created_at"],
            }
            for s in result.data
        ] if result.data else []

    async def add_message(self, session_id: UUID, message: BaseMessage) -> bool:
        """Add a message to a session in Supabase."""
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        content = message.content if hasattr(message, "content") else str(message)

        data = {
            "session_id": str(session_id),
            "role": role,
            "content": content,
        }

        try:
            await asyncio.to_thread(self._insert_message, data)
            return True
        except Exception:
            logger.exception("Error adding message to Supabase")
            return False

    async def get_messages(self, session_id: UUID) -> list[BaseMessage]:
        """Get all messages in a session from Supabase."""
        result = await asyncio.to_thread(self._select_messages, str(session_id))

        messages: list[BaseMessage] = []
        if result.data:
            for msg in result.data:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        return messages

    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and its messages from Supabase."""
        try:
            await asyncio.to_thread(self._delete_session, str(session_id))
            return True
        except Exception:
            logger.exception("Error deleting session from Supabase")
            return False

    # ------------------------------------------------------------------
    # Private synchronous helpers (run in thread)
    # ------------------------------------------------------------------

    def _insert_session(self, data: dict):
        return self.db.table("chat_sessions").insert(data).execute()

    def _select_session(self, session_id: str):
        return (
            self.db.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .execute()
        )

    def _select_sessions_by_user(self, user_id: str):
        return (
            self.db.table("chat_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

    def _insert_message(self, data: dict):
        return self.db.table("chat_messages").insert(data).execute()

    def _select_messages(self, session_id: str):
        return (
            self.db.table("chat_messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

    def _delete_session(self, session_id: str):
        # Messages are deleted via CASCADE in DB
        return (
            self.db.table("chat_sessions")
            .delete()
            .eq("id", session_id)
            .execute()
        )
