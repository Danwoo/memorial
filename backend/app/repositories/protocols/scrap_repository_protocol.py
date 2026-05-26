"""ScrapRepository 인터페이스 (의존성 역전).

ScrapInDB 도메인 모델은 이미 핵심 CRUD에 적용되어 있다. 분석/통계/내보내기성
메서드는 dict 유지(필드 셋이 가변적이라 모델 강제 시 유지 비용 큼).

Service 계층은 이 Protocol에만 의존하며, 구체 구현(`ScrapRepository`)을 모른다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from app.schemas.scrap_schema import ScrapInDB, SourceType


@runtime_checkable
class ScrapRepositoryProtocol(Protocol):
    """Scrap 영속화 인터페이스."""

    # ---- 도메인 모델 시그니처 ----
    async def create(
        self,
        user_id: UUID,
        title: str,
        content: str,
        source_type: SourceType,
        source_url: str | None = None,
        summary: str | None = None,
    ) -> ScrapInDB: ...

    async def get_by_id(self, memory_id: UUID, user_id: UUID) -> ScrapInDB | None: ...

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
    ) -> tuple[list[ScrapInDB], int]: ...

    async def update_fields(
        self,
        memory_id: UUID,
        user_id: UUID,
        **fields: object,
    ) -> ScrapInDB | None: ...

    # ---- dict 시그니처 (분석/통계/내보내기 — 필드 셋이 가변적) ----
    async def get_all(
        self,
        user_id: UUID | None = None,
        limit: int = 1000,
    ) -> list[dict]: ...

    async def get_by_date_range(
        self,
        user_id: UUID,
        start: str,
        end: str,
        limit: int = 1000,
    ) -> list[dict]: ...

    async def get_all_for_export(self, user_id: UUID, limit: int = 10000) -> list[dict]: ...

    async def get_all_with_entities(self, user_id: UUID, limit: int = 10000) -> list[dict]: ...

    # ---- 메타데이터 / mutation ----
    async def update_status(
        self,
        memory_id: UUID,
        status: str,
        summary: str | None = None,
        tags: list[str] | None = None,
        source_type: str | None = None,
        extracted_entities: list[dict] | None = None,
        extracted_relations: list[dict] | None = None,
        user_id: UUID | None = None,
    ) -> bool: ...

    async def get_distinct_tags(self, user_id: UUID, prefix: str = "") -> list[str]: ...

    async def update_tags(self, memory_id: UUID, user_id: UUID, tags: list[str]) -> bool: ...

    async def delete(self, memory_id: UUID, user_id: UUID) -> bool: ...

    async def delete_bulk(self, memory_ids: list[UUID], user_id: UUID) -> int: ...

    async def update_search_tokens(self, memory_id: str, token_string: str) -> bool: ...

    async def add_tags_bulk(self, memory_ids: list[UUID], user_id: UUID, tags: list[str]) -> int: ...

    async def remove_tags_bulk(
        self,
        memory_ids: list[UUID],
        user_id: UUID,
        tags: list[str],
    ) -> int: ...
