import asyncio
import logging

logger = logging.getLogger(__name__)


class _MaintenanceMixin:
    """그래프 유지보수 책임 mixin."""

    # ------------------------------------------------------------------
    # Memory 노드 삭제
    # ------------------------------------------------------------------
    def _sync_delete_memory_node(self, memory_id: str) -> None:
        """Memory 노드와 연결된 관계를 그래프에서 삭제."""
        conn = self._get_conn()
        conn.execute(
            "MATCH (m:Memory {id: $id}) DETACH DELETE m",
            {"id": memory_id},
        )

    async def delete_memory_node(self, memory_id: str) -> None:
        """Memory 노드와 관계를 그래프에서 삭제."""
        if not self.db:
            return
        try:
            await asyncio.to_thread(self._sync_delete_memory_node, memory_id)
        except Exception:
            logger.exception("Error deleting memory node '%s' from graph", memory_id)
