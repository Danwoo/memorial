import asyncio
import logging

from app.repositories.mindmap._constants import (
    MAX_GRAPH_TRAVERSAL_DEPTH,
    MAX_RELATED_CONTEXT_RESULTS,
)

logger = logging.getLogger(__name__)


class _EgoMixin:
    """관련 컨텍스트 및 Ego Graph 조회 mixin."""

    # ------------------------------------------------------------------
    # 관련 컨텍스트 조회 (Socrates 챗용)
    # ------------------------------------------------------------------
    def _sync_get_related_context(self, topic: str, depth: int) -> list[dict]:
        """주제와 직접 연결된 엔티티 탐색 동기 구현 (depth=1, 실제 rel_type 반환)."""
        conn = self._get_conn()
        # depth=1 직접 쿼리로 엣지 속성(rel_type) 접근
        query = f"""
        MATCH (start:Entity {{name: $topic}})-[r:ENTITY_REL]->(related:Entity)
        WHERE related.name IS NOT NULL AND related.name <> $topic
        RETURN DISTINCT
            related.name AS name,
            related.type AS label,
            r.rel_type AS rel_type,
            1 AS distance
        LIMIT {MAX_RELATED_CONTEXT_RESULTS}
        """
        return self._result_to_dicts(conn.execute(query, {"topic": topic}))

    async def get_related_context(self, topic: str, depth: int = 2) -> list[dict]:
        """Knowledge Graph에서 주제와 N-hop 이내 관련 엔티티 조회.

        Args:
            topic: 검색 주제 (엔티티 이름)
            depth: 탐색 깊이 (기본 2)
        """
        if not self.db:
            return []
        try:
            return await asyncio.to_thread(self._sync_get_related_context, topic, depth)
        except Exception:
            logger.exception("Error fetching related context for '%s'", topic)
            return []

    # ------------------------------------------------------------------
    # Ego Graph (N-hop 서브그래프) 조회
    # ------------------------------------------------------------------
    def _sync_get_ego_graph(self, node_name: str, depth: int, user_id: str) -> dict[str, list]:
        """중심 노드에서 N-hop 이내 서브그래프 조회 동기 구현."""
        conn = self._get_conn()
        safe_depth = max(1, min(depth, MAX_GRAPH_TRAVERSAL_DEPTH))

        # 중심 노드 존재 여부 확인 (해당 사용자의 Memory에 연결된 것만)
        center_check = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(center:Entity {name: $name})
        RETURN center.name AS name, center.type AS type
        LIMIT 1
        """
        center_rows = self._result_to_dicts(conn.execute(center_check, {"user_id": user_id, "name": node_name}))
        if not center_rows:
            return {"nodes": [], "links": []}

        center = center_rows[0]

        # N-hop 이내 연결된 엔티티 수집 (사용자 소유 엔티티만)
        neighbor_query = f"""
        MATCH (center:Entity {{name: $name}})-[:ENTITY_REL*1..{safe_depth}]-(neighbor:Entity)
        WHERE neighbor.name <> $name
          AND EXISTS {{ MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(neighbor) }}
        RETURN DISTINCT neighbor.name AS name, neighbor.type AS type
        """
        neighbor_rows = self._result_to_dicts(conn.execute(neighbor_query, {"name": node_name, "user_id": user_id}))

        # 중심 노드만 있고 연결 없는 경우 → 단일 노드 반환
        if not neighbor_rows:
            node = self._make_node(center["name"], center.get("type", "Unknown"))
            return {"nodes": [node], "links": []}

        # 서브그래프 내부 엔티티 간 모든 ENTITY_REL 링크 조회
        # KuzuDB는 IN 리스트 파라미터를 직접 지원하지 않으므로 개별 쿼리 조합
        internal_query = f"""
        MATCH (mem:Memory {{user_id: $user_id}})-[:MENTIONS]->(a:Entity)-[r:ENTITY_REL]->(b:Entity)<-[:MENTIONS]-(mem2:Memory {{user_id: $user_id}})
        WHERE a.name = $name OR EXISTS {{ MATCH (center:Entity {{name: $name}})-[:ENTITY_REL*1..{safe_depth}]-(a) }}
        WITH a, r, b
        WHERE (b.name = $name OR EXISTS {{ MATCH (center2:Entity {{name: $name}})-[:ENTITY_REL*1..{safe_depth}]-(b) }})
        RETURN DISTINCT
            a.name AS source_name, a.type AS source_label,
            b.name AS target_name, b.type AS target_label,
            r.rel_type AS rel_type
        """
        internal_rows = self._result_to_dicts(conn.execute(internal_query, {"name": node_name, "user_id": user_id}))

        # _build_graph_structures로 노드/링크 생성
        nodes, links = self._build_graph_structures(internal_rows)

        # 중심 노드가 링크에 없어도 반드시 포함
        if node_name not in nodes:
            nodes[node_name] = self._make_node(center["name"], center.get("type", "Unknown"))

        # 이웃 노드 중 링크에 포함되지 않은 것도 추가
        for row in neighbor_rows:
            name = row["name"]
            if name not in nodes:
                nodes[name] = self._make_node(name, row.get("type", "Unknown"))

        return {"nodes": list(nodes.values()), "links": links}

    async def get_ego_graph(self, node_name: str, depth: int = 1, user_id: str | None = None) -> dict[str, list]:
        """중심 노드 기준 N-hop Ego Graph 조회.

        Args:
            node_name: 중심 엔티티 이름
            depth: 탐색 깊이 (기본 1, 최대 MAX_GRAPH_TRAVERSAL_DEPTH)
            user_id: 사용자 ID (필수 — 미지정 시 빈 그래프 반환)
        """
        if not self.db or not user_id:
            return {"nodes": [], "links": []}
        safe_depth = max(1, min(depth, MAX_GRAPH_TRAVERSAL_DEPTH))
        try:
            return await asyncio.to_thread(self._sync_get_ego_graph, node_name, safe_depth, user_id)
        except Exception:
            logger.exception("Ego graph 조회 실패: node='%s'", node_name)
            return {"nodes": [], "links": []}

    def _sync_get_default_ego_node(self, user_id: str) -> str | None:
        """ENTITY_REL 연결 수가 가장 많은 엔티티 이름 반환 (동기)."""
        conn = self._get_conn()
        query = """
        MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)-[r:ENTITY_REL]-(:Entity)
        WITH e.name AS name, count(r) AS degree
        ORDER BY degree DESC
        LIMIT 1
        RETURN name
        """
        rows = self._result_to_dicts(conn.execute(query, {"user_id": user_id}))
        if rows:
            return rows[0].get("name")
        return None

    async def get_default_ego_node(self, user_id: str) -> str | None:
        """사용자의 가장 연결이 많은 엔티티 이름을 기본 Ego 중심 노드로 반환."""
        if not self.db:
            return None
        try:
            return await asyncio.to_thread(self._sync_get_default_ego_node, user_id)
        except Exception:
            logger.exception("기본 ego 노드 조회 실패: user_id='%s'", user_id)
            return None
