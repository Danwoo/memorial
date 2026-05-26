import asyncio
import logging

from app.repositories.mindmap._constants import MAX_GRAPH_QUERY_LIMIT

logger = logging.getLogger(__name__)


class _CentralityMixin:
    """인사이트 분석용 조회 (전체 엣지/허브/고아) mixin."""

    def _sync_get_all_edges(self, user_id: str) -> list[dict]:
        """클러스터 분석용 전체 엔티티 관계 동기 조회."""
        conn = self._get_conn()
        query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(a:Entity)-[r:ENTITY_REL]->(b:Entity)<-[:MENTIONS]-(mem2:Memory {user_id: $user_id})
        RETURN DISTINCT a.name AS source, a.type AS source_type, b.name AS target, b.type AS target_type, r.rel_type AS rel_type
        """
        return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

    async def get_all_edges(self, user_id: str) -> list[dict]:
        """클러스터 분석용 전체 엔티티 관계 조회."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_all_edges, user_id)
        except Exception:
            logger.exception("Error fetching all edges")
            return []

    def _sync_get_hub_nodes(self, user_id: str, top_n: int) -> list[dict]:
        """degree 기준 상위 N 노드 동기 조회."""
        conn = self._get_conn()
        query = f"""
        MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(e:Entity)-[r:ENTITY_REL]-(:Entity)
        WITH e.name AS name, e.type AS type, count(r) AS degree
        ORDER BY degree DESC
        LIMIT {max(1, min(top_n, 20))}
        RETURN name, type, degree
        """
        return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

    async def get_hub_nodes(self, user_id: str, top_n: int = 5) -> list[dict]:
        """degree 기준 상위 N 허브 노드 조회."""
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_hub_nodes, user_id, top_n)
        except Exception:
            logger.exception("Error fetching hub nodes")
            return []

    async def get_hub_entities(self, user_id: str, limit: int = 10) -> list[dict]:
        """연결 수 기준 상위 N 허브 엔티티 조회. connection_count 키로 연결 수 반환.

        Args:
            user_id: 사용자 ID
            limit: 반환할 최대 엔티티 수 (기본 10)
        """
        rows = await self.get_hub_nodes(user_id=user_id, top_n=limit)
        # get_hub_nodes의 "degree" 키를 "connection_count"로 변환
        return [
            {
                "name": r.get("name", ""),
                "type": r.get("type", "Concept"),
                "connection_count": int(r.get("degree", 0)),
            }
            for r in rows
        ]

    def _sync_get_orphan_entities(self, user_id: str, limit: int) -> list[dict]:
        """관계 없는 고아 엔티티 동기 조회."""
        conn = self._get_conn()
        safe_limit = max(1, min(int(limit), MAX_GRAPH_QUERY_LIMIT))
        query = f"""
        MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(e:Entity)
        WHERE NOT EXISTS {{ MATCH (e)-[:ENTITY_REL]->(:Entity) }}
          AND NOT EXISTS {{ MATCH (:Entity)-[:ENTITY_REL]->(e) }}
        RETURN DISTINCT e.name AS name, e.type AS type
        LIMIT {safe_limit}
        """
        return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

    async def get_orphan_entities(self, user_id: str, limit: int = 100) -> list[dict]:
        """관계 없는 고아 엔티티 조회.

        Args:
            user_id: 사용자 ID
            limit: 반환할 최대 엔티티 수 (기본 100)
        """
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_orphan_entities, user_id, limit)
        except Exception:
            logger.exception("Error fetching orphan entities")
            return []
