import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from supabase import Client

from app.schemas.memory_schema import MemoryInDB, SourceType
from app.utils import parse_iso_datetime
from app.utils.cache import tags_cache

logger = logging.getLogger(__name__)


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

        raise RuntimeError("Failed to create memory: DB returned no data")

    async def get_by_id(self, memory_id: UUID, user_id: UUID) -> MemoryInDB | None:
        """ID로 단일 Memory 조회 (user_id는 RLS용)."""
        try:
            result = await asyncio.to_thread(self._select_single, str(memory_id), str(user_id))
            if result.data:
                return self._row_to_model(result.data)
        except Exception:
            logger.warning("Memory lookup failed: id=%s, user=%s", memory_id, user_id, exc_info=True)
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
        tags: list[str] | None = None,
        source_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[MemoryInDB], int]:
        """사용자별 페이지네이션 Memory 목록 조회. (items, total_count) 반환."""
        result = await asyncio.to_thread(
            self._select_by_user,
            str(user_id),
            page,
            limit,
            search,
            tags,
            source_type,
            date_from,
            date_to,
            sort_by,
            sort_order,
        )

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

    async def update_fields(
        self,
        memory_id: UUID,
        user_id: UUID,
        **fields: object,
    ) -> MemoryInDB | None:
        """사용자 소유 Memory의 지정 필드를 업데이트. 업데이트된 레코드 반환."""
        now = datetime.now(UTC).isoformat()
        update_data: dict = {"updated_at": now}
        for key, val in fields.items():
            if val is not None:
                update_data[key] = val

        result = await asyncio.to_thread(
            self._update_with_owner,
            str(memory_id),
            str(user_id),
            update_data,
        )
        if result.data and len(result.data) > 0:
            return self._row_to_model(result.data[0])
        return None

    async def get_distinct_tags(self, user_id: UUID, prefix: str = "") -> list[str]:
        """사용자의 모든 메모리에서 고유 태그 목록 추출 (10분 TTL 캐시)."""
        cache_key = f"user:{user_id}:tags"
        if not prefix:
            cached = tags_cache.get(cache_key)
            if cached is not None:
                return cached

        result = await asyncio.to_thread(self._select_tags, str(user_id))
        all_tags: set[str] = set()
        for row in result.data or []:
            tags = row.get("tags")
            if tags:
                for tag in tags:
                    if isinstance(tag, str) and tag.lower().startswith(prefix.lower()):
                        all_tags.add(tag)
        sorted_tags = sorted(all_tags)

        if not prefix:
            tags_cache.set(cache_key, sorted_tags)
        return sorted_tags

    async def delete(self, memory_id: UUID, user_id: UUID) -> bool:
        """Memory 삭제."""
        result = await asyncio.to_thread(self._delete, str(memory_id), str(user_id))
        return len(result.data) > 0 if result.data else False

    async def delete_bulk(self, memory_ids: list[UUID], user_id: UUID) -> int:
        """여러 Memory 일괄 삭제. 삭제된 건수 반환."""
        str_ids = [str(mid) for mid in memory_ids]
        result = await asyncio.to_thread(self._delete_bulk, str_ids, str(user_id))
        return len(result.data) if result.data else 0

    async def add_tags_bulk(self, memory_ids: list[UUID], user_id: UUID, tags: list[str]) -> int:
        """여러 Memory에 태그 추가 (기존 태그에 합집합)."""
        str_ids = [str(mid) for mid in memory_ids]
        rows = await asyncio.to_thread(self._select_tags_for_ids, str_ids, str(user_id))
        updated = 0
        for row in rows.data or []:
            existing = row.get("tags") or []
            merged = list(dict.fromkeys(existing + tags))
            if merged != existing:
                await asyncio.to_thread(
                    self._update_with_owner,
                    row["id"],
                    str(user_id),
                    {"tags": merged, "updated_at": datetime.now(UTC).isoformat()},
                )
                updated += 1
        return updated

    async def remove_tags_bulk(self, memory_ids: list[UUID], user_id: UUID, tags: list[str]) -> int:
        """여러 Memory에서 태그 제거."""
        str_ids = [str(mid) for mid in memory_ids]
        tags_set = set(tags)
        rows = await asyncio.to_thread(self._select_tags_for_ids, str_ids, str(user_id))
        updated = 0
        for row in rows.data or []:
            existing = row.get("tags") or []
            filtered = [t for t in existing if t not in tags_set]
            if filtered != existing:
                await asyncio.to_thread(
                    self._update_with_owner,
                    row["id"],
                    str(user_id),
                    {"tags": filtered, "updated_at": datetime.now(UTC).isoformat()},
                )
                updated += 1
        return updated

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

    def _select_by_user(
        self,
        user_id: str,
        page: int,
        limit: int,
        search: str | None,
        tags: list[str] | None = None,
        source_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        offset = (page - 1) * limit
        query = self.db.table("memories").select("*", count="exact").eq("user_id", user_id)

        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.or_(f"title.ilike.%{escaped}%,content.ilike.%{escaped}%")

        if source_type:
            query = query.eq("source_type", source_type)

        if date_from:
            query = query.gte("created_at", date_from)

        if date_to:
            query = query.lte("created_at", date_to + "T23:59:59")

        if tags:
            query = query.contains("tags", tags)

        allowed_sort = {"created_at", "updated_at", "title"}
        col = sort_by if sort_by in allowed_sort else "created_at"
        query = query.order(col, desc=(sort_order == "desc")).range(offset, offset + limit - 1)
        return query.execute()

    def _update(self, memory_id: str, update_data: dict):
        return self.db.table("memories").update(update_data).eq("id", memory_id).execute()

    def _update_with_owner(self, memory_id: str, user_id: str, update_data: dict):
        return self.db.table("memories").update(update_data).eq("id", memory_id).eq("user_id", user_id).execute()

    def _select_tags(self, user_id: str):
        return self.db.table("memories").select("tags").eq("user_id", user_id).not_.is_("tags", "null").execute()

    def _delete(self, memory_id: str, user_id: str):
        return self.db.table("memories").delete().eq("id", memory_id).eq("user_id", user_id).execute()

    def _delete_bulk(self, memory_ids: list[str], user_id: str):
        return self.db.table("memories").delete().in_("id", memory_ids).eq("user_id", user_id).execute()

    def _select_tags_for_ids(self, memory_ids: list[str], user_id: str):
        return self.db.table("memories").select("id,tags").in_("id", memory_ids).eq("user_id", user_id).execute()

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
