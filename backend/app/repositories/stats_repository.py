"""
Stats Repository
Data access layer for statistics queries from Supabase.

All public methods are async and delegate synchronous Supabase calls
to a thread via ``asyncio.to_thread`` so that the event loop is never blocked.
"""
import asyncio
from datetime import datetime
from typing import Any

from supabase import Client


class StatsRepository:
    """Repository for statistics data queries."""

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def get_all_memories(self) -> list[dict[str, Any]]:
        """Get all memories for statistics calculation."""
        result = await asyncio.to_thread(self._select_all)
        return result.data or []

    async def get_memories_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Get memories created within a date range."""
        result = await asyncio.to_thread(
            self._select_range, start_date.isoformat(), end_date.isoformat()
        )
        return result.data or []

    async def get_memories_by_date(
        self,
        page: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get memories ordered by date for timeline."""
        offset = (page - 1) * limit
        result = await asyncio.to_thread(
            self._select_by_date, offset, limit
        )
        return result.data or []

    async def count_by_source_type(self) -> dict[str, int]:
        """Count memories grouped by source type."""
        result = await asyncio.to_thread(self._select_source_types)

        counts: dict[str, int] = {}
        for row in result.data or []:
            source_type = row.get("source_type", "UNKNOWN")
            counts[source_type] = counts.get(source_type, 0) + 1

        return counts

    async def get_tag_counts(self, limit: int = 10) -> dict[str, int]:
        """Get top tags by usage count."""
        result = await asyncio.to_thread(self._select_tags)

        tag_counts: dict[str, int] = {}
        for row in result.data or []:
            tags = row.get("tags") or []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:limit])

    # ------------------------------------------------------------------
    # Private synchronous helpers (run in thread)
    # ------------------------------------------------------------------

    def _select_all(self):
        return self.db.table("memories").select("*").execute()

    def _select_range(self, start_iso: str, end_iso: str):
        return (
            self.db.table("memories")
            .select("*")
            .gte("created_at", start_iso)
            .lte("created_at", end_iso)
            .execute()
        )

    def _select_by_date(self, offset: int, limit: int):
        return (
            self.db.table("memories")
            .select("id, title, summary, source_type, tags, created_at")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    def _select_source_types(self):
        return self.db.table("memories").select("source_type").execute()

    def _select_tags(self):
        return self.db.table("memories").select("tags").execute()
