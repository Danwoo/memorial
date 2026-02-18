import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from supabase import Client


class JournalRepository:
    """journals 테이블 데이터 접근 계층."""

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # 공개 비동기 인터페이스
    # ------------------------------------------------------------------

    async def create_journal(
        self,
        user_id: UUID | None = None,
        content: str = "",
        mood: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """새 저널 항목 생성."""
        data: dict[str, Any] = {
            "content": content,
            "mood": mood,
            "tags": tags or [],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
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
        """사용자의 저널 목록 조회."""
        response = await asyncio.to_thread(self._select_by_user, str(user_id), limit, offset)
        return response.data

    async def update_journal(
        self,
        journal_id: UUID,
        content: str,
        mood: str | None = None,
    ) -> dict[str, Any] | None:
        """저널 항목 수정."""
        data: dict[str, Any] = {
            "content": content,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if mood:
            data["mood"] = mood

        response = await asyncio.to_thread(self._update, str(journal_id), data)
        return response.data[0] if response.data else None

    async def get_journal_dates(
        self,
        user_id: UUID,
        limit: int = 90,
    ) -> list[dict[str, Any]]:
        """저널이 존재하는 날짜 목록 조회 (최근 limit일 기준)."""
        response = await asyncio.to_thread(self._select_dates, str(user_id), limit)
        return response.data

    async def get_journals_by_date(
        self,
        user_id: UUID,
        date_str: str,
    ) -> list[dict[str, Any]]:
        """특정 날짜의 저널 목록 조회 (YYYY-MM-DD 형식)."""
        response = await asyncio.to_thread(self._select_by_date, str(user_id), date_str)
        return response.data

    async def get_journals_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """날짜 범위 내 저널 목록 조회."""
        response = await asyncio.to_thread(
            self._select_range,
            str(user_id),
            start.isoformat(),
            end.isoformat(),
        )
        return response.data

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
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

    def _select_dates(self, user_id: str, limit: int):
        return (
            self.db.table("journals")
            .select("id, created_at, mood")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _select_by_date(self, user_id: str, date_str: str):
        return (
            self.db.table("journals")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", f"{date_str}T00:00:00")
            .lt("created_at", f"{date_str}T23:59:59.999999")
            .order("created_at", desc=True)
            .execute()
        )

    def _select_range(self, user_id: str, start_iso: str, end_iso: str):
        return (
            self.db.table("journals")
            .select("id, created_at")
            .eq("user_id", user_id)
            .gte("created_at", start_iso)
            .lte("created_at", end_iso)
            .execute()
        )

    def _update(self, journal_id: str, data: dict):
        return self.db.table("journals").update(data).eq("id", journal_id).execute()
