"""
Journal Repository
Data access layer for journals table in Supabase
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client


class JournalRepository:
    """Repository for journal CRUD operations."""

    def __init__(self, db: Client):
        self.db = db

    def create_journal(
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

        # Only include user_id if provided (dev mode may skip)
        if user_id:
            data["user_id"] = str(user_id)

        response = self.db.table("journals").insert(data).execute()
        return response.data[0] if response.data else None

    def get_journals(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get list of journals for a user."""
        response = (
            self.db.table("journals")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data

    def update_journal(
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

        response = self.db.table("journals").update(data).eq("id", str(journal_id)).execute()
        return response.data[0] if response.data else None
