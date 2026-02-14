import asyncio
from uuid import UUID

from supabase import Client


class JournalMemoryLinkRepository:
    """journal_memory_links 테이블 데이터 접근 계층."""

    def __init__(self, db: Client):
        self.db = db

    async def sync_links(
        self,
        journal_id: UUID,
        memory_ids: list[str],
        link_type: str = "manual",
    ) -> int:
        """저널에 연결된 메모리 목록을 동기화. 기존 링크 삭제 후 새로 삽입."""
        if not memory_ids:
            return 0

        # 기존 해당 타입 링크 삭제
        await asyncio.to_thread(self._delete_by_journal_and_type, str(journal_id), link_type)

        # 새 링크 삽입
        rows = [
            {
                "journal_id": str(journal_id),
                "memory_id": mid,
                "link_type": link_type,
            }
            for mid in memory_ids
        ]
        response = await asyncio.to_thread(self._upsert_links, rows)
        return len(response.data) if response.data else 0

    async def get_journals_by_memory(self, memory_id: UUID) -> list[dict]:
        """특정 메모리를 참조한 저널 목록 조회 (역참조)."""
        response = await asyncio.to_thread(self._select_by_memory, str(memory_id))
        return response.data or []

    async def get_memory_ids_by_journal(self, journal_id: UUID) -> list[str]:
        """특정 저널에 연결된 메모리 ID 목록 조회."""
        response = await asyncio.to_thread(self._select_by_journal, str(journal_id))
        return [row["memory_id"] for row in (response.data or [])]

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _delete_by_journal_and_type(self, journal_id: str, link_type: str):
        return (
            self.db.table("journal_memory_links")
            .delete()
            .eq("journal_id", journal_id)
            .eq("link_type", link_type)
            .execute()
        )

    def _upsert_links(self, rows: list[dict]):
        return self.db.table("journal_memory_links").upsert(rows, on_conflict="journal_id,memory_id").execute()

    def _select_by_memory(self, memory_id: str):
        return (
            self.db.table("journal_memory_links")
            .select("journal_id, link_type, created_at, journals(id, content, mood, created_at)")
            .eq("memory_id", memory_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

    def _select_by_journal(self, journal_id: str):
        return self.db.table("journal_memory_links").select("memory_id").eq("journal_id", journal_id).execute()
