"""MindmapRepository 인터페이스 (의존성 역전).

KuzuDB는 raw dict 반환이 많아서 대부분 dict 시그니처 유지.
find_shortest_path만 도메인 모델(MindmapShortestPath) 반환 — reasoning trace로
다른 caller에서 attribute 접근 가능.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.domain.mindmap import MindmapShortestPath


@runtime_checkable
class MindmapRepositoryProtocol(Protocol):
    """KuzuDB 마인드맵 영속화/조회 인터페이스."""

    # ---- 기본 상태 ----
    @property
    def is_connected(self) -> bool: ...

    # ---- 저장 (배치 UNWIND) ----
    async def save_entities(
        self,
        entities: list[dict],
        source_id: str,
        user_id: str | None = None,
    ) -> None: ...

    async def save_relations(self, relations: list[dict]) -> None: ...

    # ---- 카운트 / 운영 ----
    async def count_memory_nodes(self) -> int: ...

    async def delete_memory_node(self, memory_id: str) -> None: ...

    # ---- 시각화 (D3 호환 dict) ----
    async def get_graph_data(
        self,
        limit: int = 100,
        user_id: str | None = None,
    ) -> dict[str, list]: ...

    # ---- 조회 ----
    async def get_related_context(self, topic: str, depth: int = 2) -> list[dict]: ...

    async def get_ego_graph(
        self,
        node_name: str,
        depth: int = 1,
        user_id: str | None = None,
    ) -> dict[str, list]: ...

    async def get_default_ego_node(self, user_id: str) -> str | None: ...

    async def get_all_edges(self, user_id: str) -> list[dict]: ...

    async def get_hub_nodes(self, user_id: str, top_n: int = 5) -> list[dict]: ...

    async def get_hub_entities(self, user_id: str, limit: int = 10) -> list[dict]: ...

    async def get_orphan_entities(self, user_id: str, limit: int = 100) -> list[dict]: ...

    async def search_entities_by_name(self, query: str, user_id: str) -> list[dict]: ...

    async def search_entities(self, query: str, user_id: str, **kwargs: Any) -> list[dict]: ...

    async def search_memories_by_entities(
        self,
        entity_names: list[str],
        user_id: str,
        limit: int = 10,
    ) -> list[dict]: ...

    async def search_memories_via_graph(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[dict]: ...

    async def get_entity_neighborhood(
        self,
        entity_names: list[str],
        user_id: str,
        hops: int = 2,
    ) -> list[dict]: ...

    async def get_scrap_ids_for_entities(
        self,
        entity_names: list[str],
        user_id: str,
        limit: int = 20,
    ) -> list[dict]: ...

    # ---- 그래프 reasoning ----
    async def find_shortest_path(
        self,
        source: str,
        target: str,
        user_id: str,
        max_hops: int = 3,
    ) -> MindmapShortestPath | None: ...
