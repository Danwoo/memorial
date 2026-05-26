import asyncio
import logging

import kuzu

from app.repositories.mindmap._constants import MAX_GRAPH_QUERY_LIMIT

logger = logging.getLogger(__name__)


class _VisualizationMixin:
    """그래프 시각화 데이터 조회 mixin."""

    # ------------------------------------------------------------------
    # 그래프 데이터 조회 (시각화용)
    # ------------------------------------------------------------------
    def _sync_get_graph_data(self, limit: int, user_id: str | None = None) -> dict[str, list]:
        """그래프 데이터 조회 동기 구현."""
        conn = self._get_conn()
        safe_limit = max(1, min(int(limit), MAX_GRAPH_QUERY_LIMIT))

        results = self._query_entity_relations(conn, safe_limit, user_id)
        nodes, links = self._build_graph_structures(results)

        # 관계가 없는 고아 엔티티도 포함 (사용자 Memory에 연결된 것만)
        if user_id:
            self._add_orphan_entities(conn, user_id, nodes)

        return {"nodes": list(nodes.values()), "links": links}

    def _query_entity_relations(
        self,
        conn: kuzu.Connection,
        limit: int,
        user_id: str | None,
    ) -> list[dict]:
        """엔티티 간 관계 쿼리 실행."""
        if user_id:
            query = f"""
            MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(n:Entity)-[r:ENTITY_REL]->(m:Entity)<-[:MENTIONS]-(mem2:Memory {{user_id: $user_id}})
            RETURN DISTINCT
                n.name AS source_name, n.type AS source_label,
                m.name AS target_name, m.type AS target_label,
                r.rel_type AS rel_type
            LIMIT {limit}
            """
            return self._result_to_dicts(conn.execute(query, {"user_id": user_id}))

        query = f"""
        MATCH (n:Entity)-[r:ENTITY_REL]->(m:Entity)
        RETURN
            n.name AS source_name, n.type AS source_label,
            m.name AS target_name, m.type AS target_label,
            r.rel_type AS rel_type
        LIMIT {limit}
        """
        return self._result_to_dicts(conn.execute(query))

    def _build_graph_structures(
        self,
        results: list[dict],
    ) -> tuple[dict[str, dict], list[dict]]:
        """쿼리 결과에서 D3 호환 nodes/links 구조 생성."""
        nodes: dict[str, dict] = {}
        links: list[dict] = []

        for record in results:
            source_name = record.get("source_name")
            target_name = record.get("target_name")

            if source_name and source_name not in nodes:
                nodes[source_name] = self._make_node(source_name, record.get("source_label", "Unknown"))
            if target_name and target_name not in nodes:
                nodes[target_name] = self._make_node(target_name, record.get("target_label", "Unknown"))

            if source_name and target_name:
                links.append(
                    {
                        "source": source_name,
                        "target": target_name,
                        "type": record.get("rel_type", "RELATED_TO"),
                    }
                )
                # 노드 크기 산정을 위한 degree 증가
                nodes[source_name]["val"] += 1
                nodes[target_name]["val"] += 1

        return nodes, links

    def _add_orphan_entities(
        self,
        conn: kuzu.Connection,
        user_id: str,
        nodes: dict[str, dict],
    ) -> None:
        """관계가 없는 고아 엔티티를 nodes에 추가."""
        orphan_query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)
        WHERE NOT EXISTS { MATCH (e)-[:ENTITY_REL]->(:Entity) }
          AND NOT EXISTS { MATCH (:Entity)-[:ENTITY_REL]->(e) }
        RETURN DISTINCT e.name AS name, e.type AS label
        """
        for record in self._result_to_dicts(conn.execute(orphan_query, {"user_id": user_id})):
            name = record.get("name")
            if name and name not in nodes:
                nodes[name] = self._make_node(name, record.get("label", "Unknown"))

    async def get_graph_data(self, limit: int = 100, user_id: str | None = None) -> dict[str, list]:
        """시각화용 그래프 데이터 조회. D3 호환 {nodes, links} 포맷 반환.

        Args:
            limit: 최대 결과 수 (기본 100)
            user_id: 사용자 ID (지정 시 해당 사용자 데이터만 필터링)
        """
        if not self.db:
            return {"nodes": [], "links": []}

        try:
            return await asyncio.to_thread(self._sync_get_graph_data, limit, user_id)
        except Exception:
            logger.exception("Error fetching graph data")
            return {"nodes": [], "links": []}
