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

    def _update(self, journal_id: str, data: dict):
        return self.db.table("journals").update(data).eq("id", journal_id).execute()
