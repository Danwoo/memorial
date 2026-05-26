"""DiaryRepository 인터페이스 (의존성 역전).

핵심 CRUD는 DiaryEntry 도메인 모델을 반환한다. 분석/통계/내보내기성 메서드는
결과 형태가 다양해서 dict 그대로 유지.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from app.domain.diary import DiaryEntry


@runtime_checkable
class DiaryRepositoryProtocol(Protocol):
    """다이어리 영속화 인터페이스 (의존성 역전 — Service는 이 Protocol에만 의존)."""

    async def create_diary(
        self,
        user_id: UUID | None = None,
        content: str = "",
        mood: str | None = None,
        tags: list[str] | None = None,
    ) -> DiaryEntry | None: ...

    async def get_diary_by_id(self, diary_id: str, user_id: UUID) -> DiaryEntry | None: ...

    async def get_diaries(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> list[DiaryEntry]: ...

    async def update_diary(
        self,
        diary_id: UUID,
        content: str,
        mood: str | None = None,
        tags: list[str] | None = None,
        user_id: UUID | None = None,
    ) -> DiaryEntry | None: ...

    async def get_diary_dates(self, user_id: UUID, limit: int = 90) -> list[dict[str, Any]]: ...

    async def get_diaries_by_date(self, user_id: UUID, date_str: str) -> list[DiaryEntry]: ...

    async def get_all_for_export(self, user_id: UUID, limit: int = 10000) -> list[dict]: ...

    async def get_diaries_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> list[DiaryEntry]: ...

    async def search_diaries(self, query: str, user_id: str, limit: int = 5) -> list[DiaryEntry]: ...

    async def get_emotion_trend(self, user_id: str, days: int = 7) -> list[dict[str, Any]]: ...

    async def list_diary_dates(self, user_id: str, limit: int = 30) -> list[str]: ...

    async def get_diary_statistics(self, user_id: str) -> dict[str, Any]: ...
