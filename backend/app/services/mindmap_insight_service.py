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

# ---- 응답 제한 / 우선순위 상수 ----
MAX_CLUSTERS_IN_RESPONSE = 10
MAX_ENTITIES_PER_CLUSTER = 20
MIN_COMPONENT_SIZE = 2  # 단독 노드는 클러스터로 인정 안 함

MAX_TRENDS_IN_RESPONSE = 10
TREND_WINDOW_WEEKS = 4
MIN_TREND_OCCURRENCE = 2  # 4주 합산 2회 미만은 노이즈

MAX_ISOLATED_NODES_IN_RESPONSE = 20
HUB_TOP_N = 5

# ---- LLM 요약 ----
MAX_CLUSTERS_TO_SUMMARIZE = 5  # LLM 호출 비용 제어
MAX_ENTITIES_IN_SUMMARY_PROMPT = 10
CLUSTER_SUMMARY_MAX_CHARS = 50
CLUSTER_SUMMARY_PROMPT_CHAR_HINT = 20  # LLM에게 출력 길이 가이드

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

            if len(component) >= MIN_COMPONENT_SIZE:
                clusters.append(
                    ClusterInfo(
                        cluster_id=cluster_id,
                        entities=component[:MAX_ENTITIES_PER_CLUSTER],
                        entity_types=list({node_types.get(n, "Concept") for n in component}),
                        size=len(component),
                    )
                )
                cluster_id += 1

        clusters.sort(key=lambda c: c.size, reverse=True)
        return clusters[:MAX_CLUSTERS_IN_RESPONSE]

    async def _compute_trends(self, user_id: str) -> list[TrendItem]:
        """최근 N주 태그 빈도 변화 계산 (TREND_WINDOW_WEEKS)."""
        from uuid import UUID

        now = datetime.now(UTC)
        weekly_tags: list[dict[str, int]] = []

        for week_offset in range(TREND_WINDOW_WEEKS - 1, -1, -1):
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
        midpoint = TREND_WINDOW_WEEKS // 2
        for tag in all_tags:
            counts = [wt.get(tag, 0) for wt in weekly_tags]
            total = sum(counts)
            if total < MIN_TREND_OCCURRENCE:
                continue
            # 방향 판단: 최근 절반 vs 이전 절반
            recent = sum(counts[midpoint:])
            older = sum(counts[:midpoint])
            if recent > older:
                direction = "up"
            elif recent < older:
                direction = "down"
            else:
                direction = "stable"

            trends.append(TrendItem(tag=tag, counts=counts, direction=direction))

        trends.sort(key=lambda t: sum(t.counts), reverse=True)
        return trends[:MAX_TRENDS_IN_RESPONSE]

    async def _find_isolated_nodes(self, user_id: str) -> list[IsolatedNode]:
        """고아 엔티티 조회."""
        orphans = await self.mindmap_repo.get_orphan_entities(user_id)
        return [
            IsolatedNode(name=o["name"], type=o.get("type", "Concept"))
            for o in orphans[:MAX_ISOLATED_NODES_IN_RESPONSE]
        ]

    async def _find_hub_nodes(self, user_id: str) -> list[HubNode]:
        """degree 상위 허브 노드 조회."""
        hubs = await self.mindmap_repo.get_hub_nodes(user_id, top_n=HUB_TOP_N)
        return [HubNode(name=h["name"], type=h.get("type", "Concept"), degree=h.get("degree", 0)) for h in hubs]

    async def _summarize_clusters(self, clusters: list[ClusterInfo]) -> list[ClusterInfo]:
        """클러스터에 LLM 한국어 요약 추가 (비용 제어를 위해 상위 N개만)."""
        llm = get_analytical_llm()
        for cluster in clusters[:MAX_CLUSTERS_TO_SUMMARIZE]:
            entities_str = ", ".join(cluster.entities[:MAX_ENTITIES_IN_SUMMARY_PROMPT])
            types_str = ", ".join(cluster.entity_types)
            try:
                response = await llm.ainvoke(
                    f"다음 엔티티들의 공통 주제를 한국어 한 문장({CLUSTER_SUMMARY_PROMPT_CHAR_HINT}자 이내)으로 요약하세요. "
                    f"엔티티 타입: {types_str}. 엔티티: {entities_str}. "
                    f"형식: 주제 요약만 출력."
                )
                cluster.summary = response.content.strip()[:CLUSTER_SUMMARY_MAX_CHARS]
            except Exception:
                logger.warning("클러스터 %d 요약 실패", cluster.cluster_id)
                cluster.summary = f"{cluster.entities[0]} 외 {cluster.size - 1}개"
        return clusters
