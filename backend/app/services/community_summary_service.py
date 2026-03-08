import logging
from collections import defaultdict

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.llm import get_analytical_llm
from app.repositories.mindmap_repository import MindmapRepository
from app.utils.cache import community_cache

logger = logging.getLogger(__name__)

# 요약할 최대 클러스터 수
MAX_COMMUNITIES_TO_SUMMARIZE = 5
# 요약 시 사용할 최대 엔티티 수
MAX_ENTITIES_PER_COMMUNITY = 12
# 요약 시 사용할 최대 관계 수
MAX_RELATIONS_PER_COMMUNITY = 10
# 클러스터 최소 크기 (이 미만은 무시)
MIN_CLUSTER_SIZE = 2

COMMUNITY_SUMMARY_PROMPT = """You are summarizing a knowledge cluster from a user's personal knowledge graph.

Given a set of entities and their relationships, write a 2-3 sentence summary that captures:
1. The main theme or topic of this cluster
2. Key relationships between entities (especially SUPPORTS, CONTRADICTS, LEADS_TO, CREATED_BY)
3. Why this cluster matters in the user's knowledge landscape

Input format:
Entities: [name (type), ...]
Relations: [source --RELATION_TYPE--> target, ...]

Output: A concise 2-3 sentence summary in Korean that a thinking partner could reference naturally.

Example:
Entities: React (Framework), TypeScript (Language), Next.js (Framework), Vercel (Company)
Relations: Next.js --BUILT_WITH--> React, Next.js --USES--> TypeScript, Next.js --CREATED_BY--> Vercel
Output: 사용자는 React 생태계에 깊은 관심을 갖고 있으며, 특히 Next.js를 중심으로 TypeScript와 Vercel 배포까지 연결되는 풀스택 프론트엔드 기술 스택을 탐구하고 있습니다."""


class CommunitySummaryService:
    """GraphRAG 스타일 커뮤니티 요약 — 지식 그래프의 토픽 클러스터를
    LLM이 이해할 수 있는 요약문으로 변환.

    사용자의 지식 그래프에서 밀접하게 연결된 엔티티 그룹(커뮤니티)을 감지하고,
    각 커뮤니티의 주제, 핵심 관계, 의미를 2-3문장으로 요약.
    RAG 컨텍스트에 주입하여 LLM에게 거시적 지식 구조 이해를 제공.
    """

    def __init__(self, mindmap_repo: MindmapRepository):
        self.mindmap_repo = mindmap_repo

    async def get_community_summaries(self, user_id: str) -> list[dict]:
        """캐시된 커뮤니티 요약 반환. 캐시 미스 시 재생성."""
        cache_key = f"community:{user_id}"
        cached = community_cache.get(cache_key)
        if cached is not None:
            return cached

        summaries = await self._build_community_summaries(user_id)
        community_cache.set(cache_key, summaries)
        return summaries

    def invalidate_cache(self, user_id: str) -> None:
        """사용자 커뮤니티 캐시 무효화 (스크랩 저장 후 호출)."""
        community_cache.invalidate(f"community:{user_id}")

    async def _build_community_summaries(self, user_id: str) -> list[dict]:
        """그래프 엣지에서 클러스터 감지 후 LLM 요약 생성."""
        edges = await self.mindmap_repo.get_all_edges(user_id)
        if not edges:
            return []

        communities = self._detect_communities(edges)
        if not communities:
            return []

        # 상위 N개 커뮤니티만 요약
        top_communities = communities[:MAX_COMMUNITIES_TO_SUMMARIZE]
        summaries = []
        for community in top_communities:
            summary_text = await self._generate_community_summary(community, edges)
            summaries.append(
                {
                    "entities": community["entities"],
                    "entity_types": community["entity_types"],
                    "size": community["size"],
                    "summary": summary_text,
                }
            )
        return summaries

    def _detect_communities(self, edges: list[dict]) -> list[dict]:
        """BFS connected components로 커뮤니티(클러스터) 감지."""
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

    async def _generate_community_summary(self, community: dict, all_edges: list[dict]) -> str:
        """단일 커뮤니티의 상세 요약 생성.

        엔티티 이름 + 타입 + 관계 타입까지 포함하여 2-3문장 요약.
        기존 _summarize_clusters의 20자 제한을 극복한 상세 버전.
        """
        entity_set = set(community["entities"])
        entity_names = community["entities"]

        # 커뮤니티 내부 엣지만 필터링
        internal_edges = [e for e in all_edges if e.get("source") in entity_set and e.get("target") in entity_set][
            :MAX_RELATIONS_PER_COMMUNITY
        ]

        entities_str = ", ".join(
            f"{name} ({community['entity_types'][i % len(community['entity_types'])] if community['entity_types'] else 'Concept'})"
            for i, name in enumerate(entity_names)
        )
        relations_str = ", ".join(
            f"{e['source']} --{e.get('rel_type', 'RELATED_TO')}--> {e['target']}" for e in internal_edges
        )

        input_text = f"Entities: {entities_str}"
        if relations_str:
            input_text += f"\nRelations: {relations_str}"

        try:
            llm = get_analytical_llm()
            response = await llm.ainvoke(
                [
                    SystemMessage(content=COMMUNITY_SUMMARY_PROMPT),
                    HumanMessage(content=input_text),
                ]
            )
            return response.content.strip()
        except Exception:
            logger.warning("커뮤니티 요약 생성 실패: entities=%s", entity_names[:3])
            return f"{entity_names[0]} 외 {community['size'] - 1}개 관련 지식 클러스터"
