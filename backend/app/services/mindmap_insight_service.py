import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from app.config.llm import get_analytical_llm
from app.repositories.protocols.calendar_repository_protocol import CalendarRepositoryProtocol
from app.repositories.protocols.mindmap_repository_protocol import MindmapRepositoryProtocol
from app.schemas.mindmap_insight_schema import (
    ClusterInfo,
    HubNode,
    IsolatedNode,
    MindmapInsightsResponse,
    TrendItem,
)
from app.utils.cache import insights_cache

logger = logging.getLogger(__name__)


class MindmapInsightService:
    """마인드맵 인사이트 분석 서비스."""

    def __init__(self, mindmap_repo: MindmapRepositoryProtocol, calendar_repo: CalendarRepositoryProtocol):
        self.mindmap_repo = mindmap_repo
        self.calendar_repo = calendar_repo

    async def get_insights(self, user_id: str) -> MindmapInsightsResponse:
        """4종 인사이트 분석 결과 + 클러스터 LLM 요약 반환."""
        cache_key = f"insights:{user_id}"
        cached = insights_cache.get(cache_key)
        if cached is not None:
            return cached

        clusters = await self._detect_clusters(user_id)
        trends = await self._compute_trends(user_id)
        isolated = await self._find_isolated_nodes(user_id)
        hubs = await self._find_hub_nodes(user_id)

        if clusters:
            clusters = await self._summarize_clusters(clusters)

        result = MindmapInsightsResponse(
            clusters=clusters,
            trends=trends,
            isolated_nodes=isolated,
            hub_nodes=hubs,
        )
        insights_cache.set(cache_key, result)
        return result

    async def _detect_clusters(self, user_id: str) -> list[ClusterInfo]:
        """Python connected components로 클러스터 감지."""
        edges = await self.mindmap_repo.get_all_edges(user_id)
        if not edges:
            return []

        # 인접 리스트 구축
        adj: dict[str, set[str]] = defaultdict(set)
        node_types: dict[str, str] = {}
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src and tgt:
                adj[src].add(tgt)
                adj[tgt].add(src)
                if src not in node_types:
                    node_types[src] = edge.get("source_type", "Concept")
                if tgt not in node_types:
                    node_types[tgt] = edge.get("target_type", "Concept")

        # BFS로 connected components 탐색
        visited: set[str] = set()
        clusters: list[ClusterInfo] = []
        cluster_id = 0

        for node in adj:
            if node in visited:
                continue
            component: list[str] = []
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)
                for neighbor in adj[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            if len(component) >= 2:
                clusters.append(
                    ClusterInfo(
                        cluster_id=cluster_id,
                        entities=component[:20],
                        entity_types=list({node_types.get(n, "Concept") for n in component}),
                        size=len(component),
                    )
                )
                cluster_id += 1

        clusters.sort(key=lambda c: c.size, reverse=True)
        return clusters[:10]

    async def _compute_trends(self, user_id: str) -> list[TrendItem]:
        """최근 4주 태그 빈도 변화 계산."""
        from uuid import UUID

        now = datetime.now(UTC)
        weekly_tags: list[dict[str, int]] = []

        for week_offset in range(3, -1, -1):
            start = now - timedelta(weeks=week_offset + 1)
            end = now - timedelta(weeks=week_offset)
            memories = await self.calendar_repo.get_scraps_in_range(
                UUID(user_id),
                start,
                end,
            )
            tag_count: dict[str, int] = {}
            for mem in memories:
                for tag in mem.get("tags") or []:
                    tag_count[tag] = tag_count.get(tag, 0) + 1
            weekly_tags.append(tag_count)

        # 태그별 4주 카운트 집계
        all_tags: set[str] = set()
        for wt in weekly_tags:
            all_tags.update(wt.keys())

        trends: list[TrendItem] = []
        for tag in all_tags:
            counts = [wt.get(tag, 0) for wt in weekly_tags]
            total = sum(counts)
            if total < 2:
                continue
            # 방향 판단: 최근 2주 vs 이전 2주
            recent = sum(counts[2:])
            older = sum(counts[:2])
            if recent > older:
                direction = "up"
            elif recent < older:
                direction = "down"
            else:
                direction = "stable"

            trends.append(TrendItem(tag=tag, counts=counts, direction=direction))

        trends.sort(key=lambda t: sum(t.counts), reverse=True)
        return trends[:10]

    async def _find_isolated_nodes(self, user_id: str) -> list[IsolatedNode]:
        """고아 엔티티 조회."""
        orphans = await self.mindmap_repo.get_orphan_entities(user_id)
        return [IsolatedNode(name=o["name"], type=o.get("type", "Concept")) for o in orphans[:20]]

    async def _find_hub_nodes(self, user_id: str) -> list[HubNode]:
        """degree 상위 5개 허브 노드 조회."""
        hubs = await self.mindmap_repo.get_hub_nodes(user_id, top_n=5)
        return [HubNode(name=h["name"], type=h.get("type", "Concept"), degree=h.get("degree", 0)) for h in hubs]

    async def _summarize_clusters(self, clusters: list[ClusterInfo]) -> list[ClusterInfo]:
        """클러스터에 LLM 한국어 요약 추가."""
        llm = get_analytical_llm()
        for cluster in clusters[:5]:
            entities_str = ", ".join(cluster.entities[:10])
            types_str = ", ".join(cluster.entity_types)
            try:
                response = await llm.ainvoke(
                    f"다음 엔티티들의 공통 주제를 한국어 한 문장(20자 이내)으로 요약하세요. "
                    f"엔티티 타입: {types_str}. 엔티티: {entities_str}. "
                    f"형식: 주제 요약만 출력."
                )
                cluster.summary = response.content.strip()[:50]
            except Exception:
                logger.warning("클러스터 %d 요약 실패", cluster.cluster_id)
                cluster.summary = f"{cluster.entities[0]} 외 {cluster.size - 1}개"
        return clusters
