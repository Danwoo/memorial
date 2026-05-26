"""DiaryRepository 인터페이스 (의존성 역전).

현재는 dict 반환 — 다음 단계로 DiaryEntry 도메인 모델로 점진 마이그레이션.
도메인 모델은 app/domain/diary.py에 이미 정의되어 있으니, 마이그레이션은
한 메서드씩 안전하게 진행하면 된다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class DiaryRepositoryProtocol(Protocol):
    """다이어리 영속화 인터페이스 (의존성 역전 — Service는 이 Protocol에만 의존)."""

    async def create_diary(
        self,
        user_id: UUID | None = None,
        content: str = "",
        mood: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None: ...

    async def get_diary_by_id(self, diary_id: str, user_id: str) -> dict[str, Any] | None: ...

    async def get_diaries(
        self,
        user_id: UUID,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    async def update_diary(
        self,
        diary_id: UUID,
        content: str,
        mood: str | None = None,
        tags: list[str] | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any] | None: ...

    async def get_diary_dates(self, user_id: UUID, limit: int = 90) -> list[dict[str, Any]]: ...

    async def get_diaries_by_date(self, user_id: UUID, date_str: str) -> list[dict[str, Any]]: ...

    async def get_all_for_export(self, user_id: UUID, limit: int = 10000) -> list[dict]: ...

    async def get_diaries_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]: ...

    async def search_diaries(self, query: str, user_id: str, limit: int = 5) -> list[dict[str, Any]]: ...

    async def get_emotion_trend(self, user_id: str, days: int = 7) -> list[dict[str, Any]]: ...

    async def list_diary_dates(self, user_id: str, limit: int = 30) -> list[str]: ...

    async def get_diary_statistics(self, user_id: str) -> dict[str, Any]: ...
