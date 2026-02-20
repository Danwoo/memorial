import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client


class StatsRepository:
    """통계 쿼리 데이터 접근 계층."""

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # 공개 비동기 인터페이스
    # ------------------------------------------------------------------

    async def get_all_memories(self, user_id: UUID) -> list[dict[str, Any]]:
        """통계 집계용 전체 Memory 조회."""
        result = await asyncio.to_thread(self._select_all, str(user_id))
        return result.data or []

    async def get_memories_in_range(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """날짜 범위 내 Memory 조회."""
        result = await asyncio.to_thread(self._select_range, str(user_id), start_date.isoformat(), end_date.isoformat())
        return result.data or []

    async def get_memories_by_date(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """타임라인용 날짜순 Memory 조회."""
        offset = (page - 1) * limit
        result = await asyncio.to_thread(self._select_by_date, str(user_id), offset, limit)
        return result.data or []

    async def count_by_source_type(self, user_id: UUID) -> dict[str, int]:
        """소스 타입별 Memory 카운트."""
        result = await asyncio.to_thread(self._select_source_types, str(user_id))

        counts: dict[str, int] = {}
        for row in result.data or []:
            source_type = row.get("source_type", "UNKNOWN")
            counts[source_type] = counts.get(source_type, 0) + 1

        return counts

    async def get_tag_counts(self, user_id: UUID, limit: int = 10) -> dict[str, int]:
        """사용 빈도 상위 태그 조회."""
        result = await asyncio.to_thread(self._select_tags, str(user_id))

        tag_counts: dict[str, int] = {}
        for row in result.data or []:
            tags = row.get("tags") or []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:limit])

    async def count_journals_in_range(self, user_id: UUID, start: datetime, end: datetime) -> int:
        """기간 내 저널 수 조회."""
        result = await asyncio.to_thread(self._count_journals_range, str(user_id), start.isoformat(), end.isoformat())
        return result.count or 0

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _select_all(self, user_id: str):
        return self.db.table("memories").select("*").eq("user_id", user_id).execute()

    def _select_range(self, user_id: str, start_iso: str, end_iso: str):
        return (
            self.db.table("memories")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", start_iso)
            .lte("created_at", end_iso)
            .execute()
        )

    def _select_by_date(self, user_id: str, offset: int, limit: int):
        return (
            self.db.table("memories")
            .select("id, title, summary, source_type, tags, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    def _count_journals_range(self, user_id: str, start_iso: str, end_iso: str):
        return (
            self.db.table("journals")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", start_iso)
            .lte("created_at", end_iso)
            .execute()
        )

    def _select_source_types(self, user_id: str):
        return self.db.table("memories").select("source_type").eq("user_id", user_id).execute()

    def _select_tags(self, user_id: str):
        return self.db.table("memories").select("tags").eq("user_id", user_id).execute()

    # ------------------------------------------------------------------
    # 스트릭 계산용 날짜 조회
    # ------------------------------------------------------------------

    async def get_all_active_dates(self, user_id: UUID) -> set[str]:
        """메모리 + 저널에서 활동한 모든 날짜(YYYY-MM-DD) 집합 반환."""
        mem_result = await asyncio.to_thread(self._select_memory_dates, str(user_id))
        journal_result = await asyncio.to_thread(self._select_journal_dates, str(user_id))

        dates: set[str] = set()
        for row in mem_result.data or []:
            ca = row.get("created_at", "")
            if ca:
                dates.add(ca[:10])
        for row in journal_result.data or []:
            ca = row.get("created_at", "")
            if ca:
                dates.add(ca[:10])
        return dates

    def _select_memory_dates(self, user_id: str):
        return self.db.table("memories").select("created_at").eq("user_id", user_id).execute()

    def _select_journal_dates(self, user_id: str):
        return self.db.table("journals").select("created_at").eq("user_id", user_id).execute()
