import asyncio
from uuid import UUID

from supabase import Client


class DiaryScrapLinkRepository:
    """diary_scrap_links 테이블 데이터 접근 계층."""

    def __init__(self, db: Client):
        self.db = db

    async def sync_links(
        self,
        diary_id: UUID,
        scrap_ids: list[str],
        link_type: str = "manual",
    ) -> int:
        """일기에 연결된 스크랩 목록을 동기화. 삽입 먼저 → 미포함 항목 삭제."""
        if not scrap_ids:
            return 0

        # 새 링크 삽입 (upsert)
        rows = [
            {
                "diary_id": str(diary_id),
                "scrap_id": mid,
                "link_type": link_type,
            }
            for mid in scrap_ids
        ]
        response = await asyncio.to_thread(self._upsert_links, rows)

        # 새 목록에 없는 기존 링크 삭제
        await asyncio.to_thread(self._delete_excluded, str(diary_id), link_type, scrap_ids)

        return len(response.data) if response.data else 0

    async def get_diaries_by_scrap(self, scrap_id: UUID) -> list[dict]:
        """특정 스크랩을 참조한 일기 목록 조회 (역참조)."""
        response = await asyncio.to_thread(self._select_by_scrap, str(scrap_id))
        return response.data or []

    async def get_scrap_ids_by_diary(self, diary_id: UUID) -> list[str]:
        """특정 일기에 연결된 스크랩 ID 목록 조회."""
        response = await asyncio.to_thread(self._select_by_diary, str(diary_id))
        return [row["scrap_id"] for row in (response.data or [])]

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _delete_by_diary_and_type(self, diary_id: str, link_type: str):
        return self.db.table("diary_scrap_links").delete().eq("diary_id", diary_id).eq("link_type", link_type).execute()

    def _delete_excluded(self, diary_id: str, link_type: str, keep_ids: list[str]):
        query = self.db.table("diary_scrap_links").delete().eq("diary_id", diary_id).eq("link_type", link_type)
        for mid in keep_ids:
            query = query.neq("scrap_id", mid)
        return query.execute()

    def _upsert_links(self, rows: list[dict]):
        return self.db.table("diary_scrap_links").upsert(rows, on_conflict="diary_id,scrap_id").execute()

    def _select_by_scrap(self, scrap_id: str):
        return (
            self.db.table("diary_scrap_links")
            .select("diary_id, link_type, created_at, diaries(id, content, mood, created_at)")
            .eq("scrap_id", scrap_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

    def _select_by_diary(self, diary_id: str):
        return self.db.table("diary_scrap_links").select("scrap_id").eq("diary_id", diary_id).execute()
