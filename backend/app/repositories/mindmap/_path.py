import asyncio
import logging

from app.domain.mindmap import MindmapShortestPath
from app.repositories.mindmap._constants import MAX_GRAPH_TRAVERSAL_DEPTH

logger = logging.getLogger(__name__)


class _PathMixin:
    """그래프 경로 탐색 책임 mixin."""

    # ------------------------------------------------------------------
    # 최단 경로 탐색 (추천 explainability) — 도메인 모델 반환
    # ------------------------------------------------------------------
    def _sync_find_shortest_path(
        self,
        source: str,
        target: str,
        user_id: str,
        max_hops: int,
    ) -> MindmapShortestPath | None:
        """두 엔티티 사이 최단 경로 동기 구현.

        - 양 끝 엔티티 모두 사용자의 Memory에 mention되어야 한다 (소유권 검증).
        - max_hops 이내 path가 없으면 None.
        """
        conn = self._get_conn()
        safe_hops = max(1, min(int(max_hops), MAX_GRAPH_TRAVERSAL_DEPTH))

        # variable-length path 후 길이 정렬로 최단 경로 1개 추출.
        # (KuzuDB의 SHORTEST 키워드 버전별 차이가 있어 portable한 방식 사용)
        query = f"""
        MATCH (a:Entity {{name: $source}}), (b:Entity {{name: $target}})
        WHERE EXISTS {{ MATCH (ma:Memory {{user_id: $user_id}})-[:MENTIONS]->(a) }}
          AND EXISTS {{ MATCH (mb:Memory {{user_id: $user_id}})-[:MENTIONS]->(b) }}
        MATCH p = (a)-[r:ENTITY_REL*1..{safe_hops}]-(b)
        RETURN
            [n IN nodes(p) | n.name] AS names,
            [rel IN rels(p) | rel.rel_type] AS rel_types,
            length(p) AS hops
        ORDER BY hops ASC
        LIMIT 1
        """
        try:
            result = conn.execute(query, {"source": source, "target": target, "user_id": user_id})
            rows = self._result_to_dicts(result)
            if not rows:
                return None
            row = rows[0]
            return MindmapShortestPath(
                names=row.get("names") or [],
                rel_types=row.get("rel_types") or [],
                hops=int(row.get("hops") or 0),
            )
        except Exception:
            logger.exception("Shortest path 쿼리 실패: %s → %s", source, target)
            return None

    async def find_shortest_path(
        self,
        source: str,
        target: str,
        user_id: str,
        max_hops: int = 3,
    ) -> MindmapShortestPath | None:
        """두 엔티티 사이 최단 경로 탐색 (사용자 KB 한정).

        Returns:
            MindmapShortestPath 도메인 모델 (.names, .rel_types, .hops, .explanation).
            연결되지 않거나 KB에 없으면 None.

        Use case:
            - 추천 explainability: "왜 이 스크랩을 추천?" → 경로 시각화
            - 분석 에이전트: 두 개념의 잠재적 관계 발견
        """
        if not self.db or not source or not target:
            return None
        return await asyncio.to_thread(
            self._sync_find_shortest_path, source, target, user_id, max_hops
        )
