import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from supabase import Client

from app.domain.diary import DiaryEntry
from app.utils import parse_iso_datetime


class DiaryRepository:
    """diaries 테이블 데이터 접근 계층.

    `DiaryRepositoryProtocol`을 만족한다 (duck typing).

    핵심 CRUD는 DiaryEntry 도메인 모델을 반환하고, 분석/통계/내보내기성 메서드는 dict 유지.
    """

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # 공개 비동기 인터페이스 (도메인 모델)
    # ------------------------------------------------------------------

    async def create_diary(
        self,
        user_id: UUID | None = None,
        content: str = "",
        mood: str | None = None,
        tags: list[str] | None = None,
    ) -> DiaryEntry | None:
        """새 다이어리 항목 생성."""
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
        if response.data:
            return _row_to_entry(response.data[0], default_user_id=user_id)
        return None

    async def get_diaries(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DiaryEntry]:
        """사용자의 다이어리 목록 조회."""
        response = await asyncio.to_thread(self._select_by_user, str(user_id), limit, offset)
        return [_row_to_entry(row, default_user_id=user_id) for row in (response.data or [])]

    async def update_diary(
        self,
        diary_id: UUID,
        content: str,
        mood: str | None = None,
        tags: list[str] | None = None,
        user_id: UUID | None = None,
    ) -> DiaryEntry | None:
        """다이어리 항목 수정. user_id가 제공되면 소유권 검증."""
        data: dict[str, Any] = {
            "content": content,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if mood:
            data["mood"] = mood
        if tags is not None:
            data["tags"] = tags

        response = await asyncio.to_thread(self._update, str(diary_id), data, str(user_id) if user_id else None)
        if response.data:
            return _row_to_entry(response.data[0], default_user_id=user_id)
        return None

    async def get_diaries_by_date(
        self,
        user_id: UUID,
        date_str: str,
    ) -> list[DiaryEntry]:
        """특정 날짜의 다이어리 목록 조회 (YYYY-MM-DD 형식)."""
        response = await asyncio.to_thread(self._select_by_date, str(user_id), date_str)
        return [_row_to_entry(row, default_user_id=user_id) for row in (response.data or [])]

    async def get_diaries_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> list[DiaryEntry]:
        """날짜 범위 내 다이어리 목록 조회."""
        response = await asyncio.to_thread(
            self._select_range,
            str(user_id),
            start.isoformat(),
            end.isoformat(),
            limit,
        )
        return [_row_to_entry(row, default_user_id=user_id) for row in (response.data or [])]

    async def get_diary_by_id(self, diary_id: str, user_id: UUID) -> DiaryEntry | None:
        """ID로 단일 다이어리 상세 조회."""
        response = await asyncio.to_thread(self._select_by_id, diary_id, str(user_id))
        if response.data:
            return _row_to_entry(response.data[0], default_user_id=user_id)
        return None

    async def search_diaries(self, query: str, user_id: str, limit: int = 5) -> list[DiaryEntry]:
        """일기를 텍스트로 검색한다."""
        response = await asyncio.to_thread(self._search_text, query, user_id, limit)
        fallback = UUID(user_id) if user_id else None
        return [_row_to_entry(row, default_user_id=fallback) for row in (response.data or [])]

    # ------------------------------------------------------------------
    # 분석/통계/내보내기 — dict 유지
    # ------------------------------------------------------------------

    async def get_diary_dates(
        self,
        user_id: UUID,
        limit: int = 90,
    ) -> list[dict[str, Any]]:
        """다이어리가 존재하는 날짜 목록 조회 (최근 limit일 기준)."""
        response = await asyncio.to_thread(self._select_dates, str(user_id), limit)
        return response.data or []

    async def get_all_for_export(self, user_id: UUID, limit: int = 10000) -> list[dict]:
        """내보내기용 전체 저널 조회."""
        result = await asyncio.to_thread(self._select_all_for_export, str(user_id), limit)
        return result.data or []

    async def get_emotion_trend(self, user_id: str, days: int = 7) -> list[dict[str, Any]]:
        """최근 N일간 감정 추세를 반환한다."""
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        response = await asyncio.to_thread(self._select_emotion_trend, user_id, cutoff)
        return response.data or []

    async def list_diary_dates(self, user_id: str, limit: int = 30) -> list[str]:
        """일기가 작성된 날짜 목록을 반환한다."""
        response = await asyncio.to_thread(self._select_dates_simple, user_id, limit)
        dates = []
        for row in response.data or []:
            created = row.get("created_at", "")
            if created:
                dates.append(created[:10])  # YYYY-MM-DD
        return dates

    async def get_diary_statistics(self, user_id: str) -> dict[str, Any]:
        """일기 작성 통계를 반환한다."""
        response = await asyncio.to_thread(self._select_stats, user_id)
        rows = response.data or []
        total = len(rows)
        mood_dist: dict[str, int] = {}
        for row in rows:
            mood = row.get("mood") or "neutral"
            mood_dist[mood] = mood_dist.get(mood, 0) + 1
        return {
            "total_count": total,
            "mood_distribution": mood_dist,
        }

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _insert(self, data: dict):
        return self.db.table("diaries").insert(data).execute()

    def _select_by_user(self, user_id: str, limit: int, offset: int):
        return (
            self.db.table("diaries")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

    def _select_dates(self, user_id: str, limit: int):
        return (
            self.db.table("diaries")
            .select("id, created_at, mood, tags")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _select_by_date(self, user_id: str, date_str: str):
        return (
            self.db.table("diaries")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", f"{date_str}T00:00:00")
            .lt("created_at", f"{date_str}T23:59:59.999999")
            .order("created_at", desc=True)
            .execute()
        )

    def _select_range(self, user_id: str, start_iso: str, end_iso: str, limit: int):
        return (
            self.db.table("diaries")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", start_iso)
            .lte("created_at", end_iso)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _select_all_for_export(self, user_id: str, limit: int):
        return (
            self.db.table("diaries")
            .select("id, content, mood, tags, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _update(self, diary_id: str, data: dict, user_id: str | None = None):
        query = self.db.table("diaries").update(data).eq("id", diary_id)
        if user_id:
            query = query.eq("user_id", user_id)
        return query.execute()

    def _select_by_id(self, diary_id: str, user_id: str):
        return self.db.table("diaries").select("*").eq("id", diary_id).eq("user_id", user_id).execute()

    def _search_text(self, query: str, user_id: str, limit: int):
        # PostgREST ilike 와일드카드 문자 이스케이프 (%, _, *, ?)
        escaped = (
            query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").replace("*", "\\*").replace("?", "\\?")
        )
        return (
            self.db.table("diaries")
            .select("*")
            .eq("user_id", user_id)
            .or_(f"title.ilike.%{escaped}%,content.ilike.%{escaped}%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _select_emotion_trend(self, user_id: str, cutoff: str):
        return (
            self.db.table("diaries")
            .select("id, title, mood, tags, created_at")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .execute()
        )

    def _select_dates_simple(self, user_id: str, limit: int):
        return (
            self.db.table("diaries")
            .select("created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _select_stats(self, user_id: str):
        return (
            self.db.table("diaries")
            .select("id, created_at, mood")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )


# ----------------------------------------------------------------------
# Row → 도메인 모델 변환
# ----------------------------------------------------------------------


def _row_to_entry(row: dict, default_user_id: UUID | None = None) -> DiaryEntry:
    """Supabase row를 DiaryEntry 도메인 모델로 변환.

    Args:
        row: DB row (dict)
        default_user_id: select 결과에 user_id 컬럼이 없거나 비어있을 때 폴백
    """
    raw_user_id = row.get("user_id")
    user_id = UUID(raw_user_id) if raw_user_id else (default_user_id or UUID(int=0))

    updated_at_raw = row.get("updated_at")
    updated_at = parse_iso_datetime(updated_at_raw) if updated_at_raw else None

    return DiaryEntry(
        id=UUID(row["id"]),
        user_id=user_id,
        content=row.get("content") or "",
        mood=row.get("mood"),
        tags=row.get("tags") or [],
        created_at=parse_iso_datetime(row["created_at"]),
        updated_at=updated_at,
    )
