import logging
from typing import Any

from app.repositories.graph_repository import GraphRepository
from app.repositories.memory_repository import MemoryRepository
from app.utils.cache import graph_cache

logger = logging.getLogger(__name__)


class GraphService:
    """Knowledge Graph 비즈니스 로직."""

    def __init__(self, graph_repo: GraphRepository, memory_repo: MemoryRepository | None = None):
        self.graph_repo = graph_repo
        self.memory_repo = memory_repo

    @property
    def is_available(self) -> bool:
        """그래프 기능 사용 가능 여부 확인."""
        return self.graph_repo.is_connected

    async def save_knowledge_graph(
        self, memory_id: str, entities: list[dict[str, Any]], relations: list[dict[str, Any]]
    ) -> bool:
        """추출된 엔티티/관계를 Knowledge Graph에 저장. Librarian 에이전트가 호출."""
        if not self.is_available:
            return False

        try:
            await self.graph_repo.save_entities(entities, memory_id)
            await self.graph_repo.save_relations(relations)
            graph_cache.clear()
            return True
        except Exception:
            logger.exception("Error saving to graph")
            return False

    async def create_relation(self, relations: list[dict[str, str]]) -> bool:
        """수동 관계 생성."""
        if not self.is_available:
            return False
        try:
            await self.graph_repo.save_relations(relations)
            graph_cache.clear()
            return True
        except Exception:
            logger.exception("Error creating relation")
            return False

    async def rebuild_from_supabase(self) -> dict[str, int]:
        """Supabase에 저장된 그래프 데이터로 KuzuDB를 리빌드.

        서버 시작 시 호출되어 영구 디스크 없이도 그래프를 복원한다.
        """
        if not self.is_available or not self.memory_repo:
            return {"memories": 0, "entities": 0, "relations": 0}

        memories = await self.memory_repo.get_all(limit=5000)
        total_entities = 0
        total_relations = 0
        rebuilt = 0

        for mem in memories:
            if mem.get("status") != "completed":
                continue

            entities = mem.get("extracted_entities") or []
            relations = mem.get("extracted_relations") or []

            if not entities and not relations:
                continue

            memory_id = mem["id"]
            user_id = mem.get("user_id")

            if entities:
                await self.graph_repo.save_entities(entities, memory_id, user_id)
                total_entities += len(entities)
            if relations:
                await self.graph_repo.save_relations(relations)
                total_relations += len(relations)
            rebuilt += 1

        graph_cache.clear()
        logger.info(
            "KuzuDB rebuild complete: %d memories, %d entities, %d relations",
            rebuilt,
            total_entities,
            total_relations,
        )
        return {"memories": rebuilt, "entities": total_entities, "relations": total_relations}

    async def get_visualization_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, Any]:
        """D3 시각화용 그래프 데이터 조회 (5분 TTL 캐시). user_id로 필터링."""
        if not self.is_available:
            return {"nodes": [], "links": []}

        cache_key = f"graph:{user_id}:{limit}"
        cached = graph_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.graph_repo.get_graph_data(limit, user_id)
        graph_cache.set(cache_key, result)
        return result

    async def get_ego_data(self, node_name: str, depth: int = 1, user_id: str | None = None) -> dict[str, Any]:
        """Ego Graph 서브그래프 조회 (5분 TTL 캐시)."""
        if not self.is_available:
            return {"nodes": [], "links": []}

        cache_key = f"graph:ego:{user_id}:{node_name}:{depth}"
        cached = graph_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.graph_repo.get_ego_graph(node_name, depth, user_id)
        graph_cache.set(cache_key, result)
        return result

    async def get_ego_default(self, user_id: str) -> dict[str, Any]:
        """기본 Ego Graph: 연결 수 최다 노드 중심 1-hop 서브그래프."""
        if not self.is_available:
            return {"nodes": [], "links": [], "center_node": None}

        center = await self.graph_repo.get_default_ego_node(user_id)
        if not center:
            return {"nodes": [], "links": [], "center_node": None}

        data = await self.get_ego_data(center, 1, user_id)
        data["center_node"] = center
        return data
