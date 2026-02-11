import logging
from typing import Any

from app.repositories.graph_repository import GraphRepository
from app.repositories.memory_repository import MemoryRepository

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
            return True
        except Exception:
            logger.exception("Error saving to graph")
            return False

    async def get_visualization_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, Any]:
        """D3 시각화용 그래프 데이터 조회. user_id로 필터링."""
        if not self.is_available:
            return {"nodes": [], "links": []}

        return await self.graph_repo.get_graph_data(limit, user_id)
