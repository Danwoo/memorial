import asyncio
import logging
from typing import Any
from uuid import UUID

from app.repositories.protocols.mindmap_repository_protocol import MindmapRepositoryProtocol
from app.repositories.protocols.scrap_repository_protocol import ScrapRepositoryProtocol
from app.utils.cache import graph_cache

logger = logging.getLogger(__name__)

# 그래프 재구축 시 CPU 블로킹 회피용 yield 간격
REBUILD_YIELD_EVERY = 10
# 단일 사용자 재구축 시 조회할 최대 스크랩 수
MAX_REBUILD_SCRAPS_PER_USER = 10000


class MindmapService:
    """Knowledge Mindmap 비즈니스 로직."""

    def __init__(self, mindmap_repo: MindmapRepositoryProtocol, scrap_repo: ScrapRepositoryProtocol | None = None):
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

    async def rebuild_for_user(self, user_id: UUID) -> dict[str, int]:
        """단일 사용자의 그래프를 Supabase에 저장된 entities/relations로 재인덱싱.

        EC2 이전 등으로 kuzu_data가 비어 있을 때 사용자 요청 시 호출된다.
        LLM 재실행 없이 DB에 이미 저장된 데이터만 사용.
        """
        if not self.is_available or not self.scrap_repo:
            return {"processed": 0, "skipped": 0}

        raw_scraps = await self.scrap_repo.get_all_with_entities(user_id, limit=MAX_REBUILD_SCRAPS_PER_USER)

        processed = 0
        skipped = 0
        for scrap in raw_scraps:
            scrap_id = scrap.get("id")
            entities = scrap.get("extracted_entities") or []
            relations = scrap.get("extracted_relations") or []

            if not scrap_id or not entities:
                skipped += 1
                continue

            await self.mindmap_repo.save_entities(entities, str(scrap_id), str(user_id))
            if relations:
                await self.mindmap_repo.save_relations(relations)

            processed += 1
            if processed % REBUILD_YIELD_EVERY == 0:
                await asyncio.sleep(0)  # 이벤트 루프 양보

        # 해당 사용자의 그래프 캐시 무효화
        graph_cache.invalidate_prefix(f"graph:{user_id}")
        graph_cache.invalidate_prefix(f"graph:ego:{user_id}")
        logger.info("그래프 재구축 완료: user=%s, processed=%d, skipped=%d", user_id, processed, skipped)
        return {"processed": processed, "skipped": skipped}

    async def get_visualization_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, Any]:
        """D3 시각화용 마인드맵 데이터 조회 (5분 TTL 캐시). user_id로 필터링.

        반환 형태가 ``{"nodes": [...], "links": [...]}`` 와이어 포맷인 것은 의도적이다.
        - 캐시는 직렬화 비용을 피하기 위해 wire 포맷 그대로 저장 (router에서 재변환 시
          캐시 hit 경로마다 변환 비용 발생).
        - 이 메서드는 read-only 시각화 전용이고 다른 비즈니스 로직이 결과를 가공하지 않는다.
        - 도메인 엔티티가 의미 있는 곳(MindmapEntity/Relation)에는 이미 도메인 모델 적용.
        """
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
