import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from supabase import Client

from app.schemas.memory_schema import MemoryInDB, SourceType
from app.utils import parse_iso_datetime


class MemoryRepository:
    """memories 테이블 데이터 접근 계층."""

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # 공개 비동기 인터페이스
    # ------------------------------------------------------------------

    async def create(
        self,
        user_id: UUID,
        title: str,
        content: str,
        source_type: SourceType,
        source_url: str | None = None,
        summary: str | None = None,
    ) -> MemoryInDB:
        """새 Memory 레코드 생성. 생성된 ID 포함 결과 반환."""
        memory_id = uuid4()
        now = datetime.now(UTC).isoformat()

        data = {
            "id": str(memory_id),
            "user_id": str(user_id),
            "title": title,
            "content": content,
            "source_type": source_type,
            "summary": summary,
            "status": "processing",
            "created_at": now,
            "updated_at": now,
        }

        result = await asyncio.to_thread(self._insert, data)

        if result.data:
            return self._row_to_model(result.data[0])

        raise Exception("Failed to create memory")

    async def get_by_id(self, memory_id: UUID, user_id: UUID) -> MemoryInDB | None:
        """ID로 단일 Memory 조회 (user_id는 RLS용)."""
        try:
            result = await asyncio.to_thread(self._select_single, str(memory_id), str(user_id))
            if result.data:
                return self._row_to_model(result.data)
        except Exception:
            pass
        return None

    async def get_all(
        self,
        user_id: UUID | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """내부 서비스용 전체 Memory 조회 (raw dict 반환)."""
        result = await asyncio.to_thread(self._select_all, str(user_id) if user_id else None, limit)
        return result.data or []

    async def get_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[MemoryInDB], int]:
        """사용자별 페이지네이션 Memory 목록 조회. (items, total_count) 반환."""
        result = await asyncio.to_thread(self._select_by_user, str(user_id), page, limit, search)

        items = [self._row_to_model(row) for row in (result.data or [])]
        total = result.count if result.count else 0
        return items, total

    async def update_status(
        self,
        memory_id: UUID,
        status: str,
        summary: str | None = None,
        tags: list[str] | None = None,
        source_url: str | None = None,
        source_type: str | None = None,
    ) -> bool:
        """Memory 상태 업데이트. 선택적으로 summary/tags도 갱신."""
        now = datetime.now(UTC).isoformat()

        update_data: dict = {"status": status, "updated_at": now}

        if summary is not None:
            update_data["summary"] = summary
        if tags is not None:
            update_data["tags"] = tags
        if source_url is not None:
            update_data["source_url"] = source_url
        if source_type is not None:
            update_data["source_type"] = source_type

        result = await asyncio.to_thread(self._update, str(memory_id), update_data)
        return len(result.data) > 0 if result.data else False

    async def delete(self, memory_id: UUID, user_id: UUID) -> bool:
        """Memory 삭제."""
        result = await asyncio.to_thread(self._delete, str(memory_id), str(user_id))
        return len(result.data) > 0 if result.data else False

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _insert(self, data: dict):
        return self.db.table("memories").insert(data).execute()

    def _select_single(self, memory_id: str, user_id: str):
        return self.db.table("memories").select("*").eq("id", memory_id).eq("user_id", user_id).single().execute()

    def _select_all(self, user_id: str | None, limit: int):
        query = self.db.table("memories").select("*")
        if user_id is not None:
            query = query.eq("user_id", user_id)
        query = query.order("created_at", desc=True).limit(limit)
        return query.execute()

    def _select_by_user(self, user_id: str, page: int, limit: int, search: str | None):
        offset = (page - 1) * limit
        query = self.db.table("memories").select("*", count="exact").eq("user_id", user_id)

        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.or_(f"title.ilike.%{escaped}%,content.ilike.%{escaped}%")

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        return query.execute()

    def _update(self, memory_id: str, update_data: dict):
        return self.db.table("memories").update(update_data).eq("id", memory_id).execute()

    def _delete(self, memory_id: str, user_id: str):
        return self.db.table("memories").delete().eq("id", memory_id).eq("user_id", user_id).execute()

    # ------------------------------------------------------------------
    # 변환
    # ------------------------------------------------------------------

    def _row_to_model(self, row: dict) -> MemoryInDB:
        """DB 행을 Pydantic 모델로 변환."""
        return MemoryInDB(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            title=row["title"],
            content=row["content"],
            summary=row.get("summary"),
            source_url=row.get("source_url"),
            source_type=row["source_type"],
            status=row.get("status", "pending"),
            tags=row.get("tags"),
            created_at=parse_iso_datetime(row["created_at"]),
            updated_at=parse_iso_datetime(row["updated_at"]) if row.get("updated_at") else None,
        )
