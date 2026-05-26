import logging
from typing import Any

from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.scrap_repository import ScrapRepository
from app.utils.cache import graph_cache

logger = logging.getLogger(__name__)


class MindmapService:
    """Knowledge Mindmap 비즈니스 로직."""

    def __init__(self, mindmap_repo: MindmapRepository, scrap_repo: ScrapRepository | None = None):
        self.mindmap_repo = mindmap_repo
        self.scrap_repo = scrap_repo

    @property
    def is_available(self) -> bool:
        """마인드맵 기능 사용 가능 여부 확인."""
        return self.mindmap_repo.is_connected

    async def save_knowledge_mindmap(
        self,
        scrap_id: str,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        user_id: str | None = None,
    ) -> bool:
        """추출된 엔티티/관계를 Knowledge Mindmap에 저장. Librarian 에이전트가 호출."""
        if not self.is_available:
            return False

        try:
            await self.mindmap_repo.save_entities(entities, scrap_id)
            await self.mindmap_repo.save_relations(relations)
            # 해당 사용자의 그래프 캐시만 무효화 (공유 Redis 전체 삭제 방지)
            if user_id:
                graph_cache.invalidate_prefix(f"graph:{user_id}")
                graph_cache.invalidate_prefix(f"graph:ego:{user_id}")
            else:
                graph_cache.invalidate_prefix("graph:")
            return True
        except Exception:
            logger.exception("Error saving to mindmap")
            return False

    async def create_relation(self, relations: list[dict[str, str]], user_id: str | None = None) -> bool:
        """수동 관계 생성."""
        if not self.is_available:
            return False
        try:
            await self.mindmap_repo.save_relations(relations)
            # 해당 사용자의 그래프 캐시만 무효화 (공유 Redis 전체 삭제 방지)
            if user_id:
                graph_cache.invalidate_prefix(f"graph:{user_id}")
                graph_cache.invalidate_prefix(f"graph:ego:{user_id}")
            else:
                graph_cache.invalidate_prefix("graph:")
            return True
        except Exception:
            logger.exception("Error creating relation")
            return False

    async def rebuild_from_supabase(self, force: bool = False) -> dict[str, int]:
        """Supabase에 저장된 마인드맵 데이터로 KuzuDB를 리빌드.

        부팅 시 호출. KuzuDB에 이미 데이터가 있으면 skip하여 영구 디스크
        환경에서 매 부팅 5000개 스크랩 재처리하는 비용을 회피한다.

        Args:
            force: True면 기존 데이터 무시하고 강제 rebuild (운영자 명령)
        """
        if not self.is_available or not self.scrap_repo:
            return {"scraps": 0, "entities": 0, "relations": 0}

        if not force:
            existing = await self.mindmap_repo.count_memory_nodes()
            if existing > 0:
                logger.info(
                    "KuzuDB rebuild skipped — %d Memory nodes already present (force=False)",
                    existing,
                )
                return {"scraps": 0, "entities": 0, "relations": 0, "skipped": True}

        scraps = await self.scrap_repo.get_all(limit=5000)
        total_entities = 0
        total_relations = 0
        rebuilt = 0

        for scrap in scraps:
            if scrap.get("status") != "completed":
                continue

            entities = scrap.get("extracted_entities") or []
            relations = scrap.get("extracted_relations") or []

            if not entities and not relations:
                continue

            scrap_id = scrap["id"]
            user_id = scrap.get("user_id")

            if entities:
                await self.mindmap_repo.save_entities(entities, scrap_id, user_id)
                total_entities += len(entities)
            if relations:
                await self.mindmap_repo.save_relations(relations)
                total_relations += len(relations)
            rebuilt += 1

        # 전체 리빌드이므로 모든 사용자의 그래프 캐시를 무효화
        graph_cache.invalidate_prefix("graph:")
        logger.info(
            "KuzuDB rebuild complete: %d scraps, %d entities, %d relations",
            rebuilt,
            total_entities,
            total_relations,
        )
        return {"scraps": rebuilt, "entities": total_entities, "relations": total_relations}

    async def get_visualization_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, Any]:
        """D3 시각화용 마인드맵 데이터 조회 (5분 TTL 캐시). user_id로 필터링."""
        if not self.is_available:
            return {"nodes": [], "links": []}

        cache_key = f"graph:{user_id}:{limit}"
        cached = graph_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.mindmap_repo.get_graph_data(limit, user_id)
        graph_cache.set(cache_key, result)
        return result

    async def get_ego_data(self, node_name: str, depth: int = 1, user_id: str | None = None) -> dict[str, Any]:
        """Ego Mindmap 서브그래프 조회 (5분 TTL 캐시)."""
        if not self.is_available:
            return {"nodes": [], "links": []}

        cache_key = f"graph:ego:{user_id}:{node_name}:{depth}"
        cached = graph_cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self.mindmap_repo.get_ego_graph(node_name, depth, user_id)
        graph_cache.set(cache_key, result)
        return result

    async def get_ego_default(self, user_id: str) -> dict[str, Any]:
        """기본 Ego Mindmap: 연결 수 최다 노드 중심 1-hop 서브그래프."""
        if not self.is_available:
            return {"nodes": [], "links": [], "center_node": None}

        center = await self.mindmap_repo.get_default_ego_node(user_id)
        if not center:
            return {"nodes": [], "links": [], "center_node": None}

        data = await self.get_ego_data(center, 1, user_id)
        data["center_node"] = center
        return data
