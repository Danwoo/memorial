"""
Journal Repository
Data access layer for journals table in Supabase.

All public methods are async and delegate synchronous Supabase calls
to a thread via ``asyncio.to_thread`` so that the event loop is never blocked.
"""
import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client


class JournalRepository:
    """Repository for journal CRUD operations."""

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def create_journal(
        self,
        user_id: UUID | None = None,
        content: str = "",
        mood: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a new journal entry."""
        data: dict[str, Any] = {
            "content": content,
            "mood": mood,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        if user_id:
            data["user_id"] = str(user_id)

        response = await asyncio.to_thread(self._insert, data)
        return response.data[0] if response.data else None

    async def get_journals(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get list of journals for a user."""
        response = await asyncio.to_thread(
            self._select_by_user, str(user_id), limit, offset
        )
        return response.data

    async def update_journal(
        self,
        journal_id: UUID,
        content: str,
        mood: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a journal entry."""
        data: dict[str, Any] = {
            "content": content,
            "updated_at": datetime.now().isoformat(),
        }
        if mood:
            data["mood"] = mood

        response = await asyncio.to_thread(
            self._update, str(journal_id), data
        )
        return response.data[0] if response.data else None

    # ------------------------------------------------------------------
    # Private synchronous helpers (run in thread)
    # ------------------------------------------------------------------

    def _insert(self, data: dict):
        return self.db.table("journals").insert(data).execute()

    def _select_by_user(self, user_id: str, limit: int, offset: int):
        return (
            self.db.table("journals")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    def _update(self, journal_id: str, data: dict):
        return (
            self.db.table("journals")
            .update(data)
            .eq("id", journal_id)
            .execute()
        )
