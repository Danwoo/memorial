"""CalendarRepository 인터페이스 (의존성 역전)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class CalendarRepositoryProtocol(Protocol):
    """캘린더 활동 집계 영속화 인터페이스."""

    async def get_all_scraps(self, user_id: UUID) -> list[dict[str, Any]]: ...

    async def get_scraps_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]: ...

    async def get_scraps_by_date(
        self,
        user_id: UUID,
        date_str: str,
    ) -> list[dict[str, Any]]: ...

    async def count_by_source_type(self, user_id: UUID) -> dict[str, int]: ...

    async def get_tag_counts(self, user_id: UUID, limit: int = 10) -> dict[str, int]: ...

    async def count_diaries_in_range(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
    ) -> int: ...

    async def get_all_active_dates(self, user_id: UUID) -> set[str]: ...
