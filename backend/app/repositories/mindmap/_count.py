import asyncio
import logging

logger = logging.getLogger(__name__)


class _CountMixin:
    """카운트 (운영 — 증분 rebuild 판정용) mixin."""

    def _sync_count_memory_nodes(self) -> int:
        """Memory 노드 총 개수 — KuzuDB가 비었는지 빠르게 판정."""
        conn = self._get_conn()
        try:
            result = conn.execute("MATCH (m:Memory) RETURN count(m) AS cnt")
            rows = self._result_to_dicts(result)
            return int(rows[0].get("cnt", 0)) if rows else 0
        except Exception:
            logger.exception("count_memory_nodes 실패")
            return 0

    async def count_memory_nodes(self) -> int:
        """KuzuDB에 저장된 Memory 노드 개수 (운영자/시작 시 idempotent 체크용)."""
        if not self.db:
            return 0
        return await asyncio.to_thread(self._sync_count_memory_nodes)
