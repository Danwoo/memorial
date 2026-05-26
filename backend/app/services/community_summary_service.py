"""커뮤니티 요약 서비스.

Supabase graph_communities 테이블에서 요약을 조회하여 반환.
GraphRAGIndexingService.reindex()로 사전 인덱싱된 데이터를 활용.
인덱싱 전이나 임베딩 미설정 시에는 BFS 폴백으로 온-디맨드 요약 생성.
"""

import logging
from collections import defaultdict

from langchain_core.messages import HumanMessage, SystemMessage
from supabase import Client

from app.config.llm import get_analytical_llm
from app.repositories.protocols.mindmap_repository_protocol import MindmapRepositoryProtocol
from app.utils.cache import community_cache

logger = logging.getLogger(__name__)

MAX_COMMUNITIES_TO_RETURN = 8
MIN_CLUSTER_SIZE = 2
MAX_ENTITIES_PER_COMMUNITY = 12
MAX_RELATIONS_PER_COMMUNITY = 10

COMMUNITY_SUMMARY_PROMPT = """You are summarizing a knowledge cluster from a user's personal knowledge graph.

Given entities and their relationships, write a 2-3 sentence summary in Korean that captures:
1. The main theme or topic of this cluster
2. Key relationships between entities
3. Why this cluster matters

Entities: {entities}
Relations: {relations}"""


class CommunitySummaryService:
    """Supabase graph_communities 기반 커뮤니티 요약 서비스.

    GraphRAGIndexingService가 사전 인덱싱한 커뮤니티 요약을 반환.
    인덱싱 데이터가 없을 때 BFS 폴백으로 온-디맨드 생성.
    """

    def __init__(self, mindmap_repo: MindmapRepositoryProtocol, db: Client | None = None):
        self.mindmap_repo = mindmap_repo
        self.db = db

    async def get_community_summaries(self, user_id: str) -> list[dict]:
        """캐시 → Supabase graph_communities → BFS 폴백 순서로 커뮤니티 요약 반환."""
        cache_key = f"community:{user_id}"
        cached = community_cache.get(cache_key)
        if cached is not None:
            return cached

        # 1. Supabase graph_communities 조회 (GraphRAG 인덱싱 결과)
        if self.db is not None:
            summaries = await self._fetch_from_supabase(user_id)
            if summaries:
                community_cache.set(cache_key, summaries)
                return summaries

        # 2. 폴백: BFS connected components + 온-디맨드 LLM 요약
        summaries = await self._build_bfs_summaries(user_id)
        community_cache.set(cache_key, summaries)
        return summaries

    def invalidate_cache(self, user_id: str) -> None:
        """사용자 커뮤니티 캐시 무효화."""
        community_cache.invalidate(f"community:{user_id}")

    # ------------------------------------------------------------------
    # Supabase 조회 (인덱싱된 GraphRAG 커뮤니티)
    # ------------------------------------------------------------------

    async def _fetch_from_supabase(self, user_id: str) -> list[dict]:
        """graph_communities level=1(mid) 기준 상위 커뮤니티 요약 반환."""
        try:
            import asyncio

            response = await asyncio.to_thread(
                lambda: self.db.table("graph_communities")
                .select("entities, entity_count, summary")
                .eq("user_id", user_id)
                .eq("level", 1)
                .not_.is_("summary", "null")
                .order("entity_count", desc=True)
                .limit(MAX_COMMUNITIES_TO_RETURN)
                .execute()
            )
            rows = response.data or []
            return [
                {
                    "entities": r.get("entities", []),
                    "entity_types": [],
                    "size": r.get("entity_count", len(r.get("entities", []))),
                    "summary": r.get("summary", ""),
                }
                for r in rows
                if r.get("summary")
            ]
        except Exception:
            logger.exception("Supabase graph_communities 조회 실패")
            return []

    # ------------------------------------------------------------------
    # BFS 폴백 (인덱싱 전 온-디맨드)
    # ------------------------------------------------------------------

    async def _build_bfs_summaries(self, user_id: str) -> list[dict]:
        """KuzuDB 엣지 → BFS connected components → LLM 요약."""
        edges = await self.mindmap_repo.get_all_edges(user_id)
        if not edges:
            return []

        communities = self._detect_bfs_communities(edges)
        if not communities:
            return []

        summaries = []
        for community in communities[:MAX_COMMUNITIES_TO_RETURN]:
            summary_text = await self._generate_summary(community, edges)
            summaries.append(
                {
                    "entities": community["entities"],
                    "entity_types": community["entity_types"],
                    "size": community["size"],
                    "summary": summary_text,
                }
            )
        return summaries

    def _detect_bfs_communities(self, edges: list[dict]) -> list[dict]:
        """BFS connected components로 커뮤니티 감지."""
        adj: dict[str, set[str]] = defaultdict(set)
        node_types: dict[str, str] = {}

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src and tgt:
                adj[src].add(tgt)
                adj[tgt].add(src)
                node_types.setdefault(src, edge.get("source_type", "Concept"))
                node_types.setdefault(tgt, edge.get("target_type", "Concept"))

        visited: set[str] = set()
        communities: list[dict] = []

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

            if len(component) >= MIN_CLUSTER_SIZE:
                communities.append(
                    {
                        "entities": component[:MAX_ENTITIES_PER_COMMUNITY],
                        "entity_types": list({node_types.get(n, "Concept") for n in component}),
                        "size": len(component),
                    }
                )

        communities.sort(key=lambda c: c["size"], reverse=True)
        return communities

    async def _generate_summary(self, community: dict, all_edges: list[dict]) -> str:
        """단일 커뮤니티 LLM 요약 생성."""
        entity_set = set(community["entities"])
        internal_edges = [e for e in all_edges if e.get("source") in entity_set and e.get("target") in entity_set][
            :MAX_RELATIONS_PER_COMMUNITY
        ]

        entities_str = ", ".join(community["entities"])
        relations_str = (
            ", ".join(f"{e['source']} --{e.get('rel_type', 'RELATED_TO')}--> {e['target']}" for e in internal_edges)
            or "없음"
        )

        prompt = COMMUNITY_SUMMARY_PROMPT.format(entities=entities_str, relations=relations_str)
        try:
            llm = get_analytical_llm()
            response = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="요약을 생성하세요.")])
            return response.content.strip()
        except Exception:
            logger.warning("커뮤니티 요약 생성 실패: entities=%s", community["entities"][:3])
            members = community["entities"]
            return f"{members[0]} 외 {community['size'] - 1}개 관련 지식 클러스터"
