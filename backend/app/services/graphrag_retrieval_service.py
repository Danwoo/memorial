"""GraphRAG 검색 서비스.

Global Search: 커뮤니티 요약 임베딩 검색 → map-reduce 합성 (광범위/개요 질문)
Local Search:  엔티티 임베딩 검색 → KuzuDB 2-hop 탐색 (구체적/특정 질문)

쿼리 분류 → 검색 방식 선택 → 컨텍스트 반환.
"""

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from supabase import Client

from app.config.llm import get_analytical_llm
from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

# Global search 판단 키워드 (한국어 + 영어)
GLOBAL_QUERY_SIGNALS = frozenset(
    {
        "전체",
        "전반",
        "전반적",
        "요약",
        "overview",
        "전체적",
        "overall",
        "summary",
        "모든",
        "다",
        "총",
        "일반",
        "주요",
        "전체적으로",
        "대체로",
        "관계",
        "패턴",
        "경향",
        "어떻게",
        "왜",
        "연결",
        "흐름",
        "구조",
    }
)

# Local search: 특정 엔티티명이나 짧은 구체적 쿼리
MATCH_TOP_K_ENTITIES = 8  # 엔티티 의미 유사도 상위 K
MATCH_TOP_K_COMMUNITIES = 6  # 커뮤니티 유사도 상위 K
GLOBAL_COMMUNITY_LEVEL = 1  # Global search 기본 레벨 (mid)
LOCAL_NEIGHBORHOOD_HOPS = 2  # Local search KuzuDB 탐색 깊이

MAP_REDUCE_PROMPT = """다음 지식 커뮤니티 요약들을 바탕으로 사용자의 질문에 간결하게 답하세요.

질문: {query}

관련 커뮤니티 요약:
{summaries}

답변 (2-4문장, 한국어):"""

LOCAL_CONTEXT_PROMPT = """다음 지식 그래프 정보를 바탕으로 사용자의 질문과 관련된 핵심 맥락을 요약하세요.

질문: {query}

관련 엔티티 및 관계:
{graph_info}

요약 (1-3문장, 한국어):"""


class GraphRAGRetrievalService:
    """Global/Local GraphRAG 검색 서비스."""

    def __init__(
        self,
        mindmap_repo: MindmapRepository,
        vector_repo: VectorRepository,
        db: Client,
    ):
        self.mindmap_repo = mindmap_repo
        self.vector_repo = vector_repo
        self.db = db

    # ------------------------------------------------------------------
    # 공개 인터페이스
    # ------------------------------------------------------------------

    async def retrieve(self, query: str, user_id: str) -> dict:
        """쿼리 분류 → Global 또는 Local 검색 실행.

        Returns:
            {"mode": "global"|"local", "context": str, "entities": list}
        """
        mode = self._classify_query(query)
        try:
            if mode == "global":
                context = await self.global_search(query, user_id)
            else:
                context = await self.local_search(query, user_id)
        except Exception:
            logger.exception("GraphRAG retrieve 실패: mode=%s, query=%.50s", mode, query)
            context = ""

        return {"mode": mode, "context": context}

    async def global_search(self, query: str, user_id: str) -> str:
        """커뮤니티 요약 임베딩 검색 → map-reduce LLM 합성."""
        embedding = await self.vector_repo.embed_query(query)
        if not embedding:
            return await self._fallback_keyword_community(query, user_id)

        communities = await asyncio.to_thread(self._search_communities, embedding, user_id, GLOBAL_COMMUNITY_LEVEL)
        if not communities:
            return ""

        summaries_text = "\n".join(
            f"[커뮤니티 {i + 1}] {c.get('summary', '')}" for i, c in enumerate(communities) if c.get("summary")
        )
        if not summaries_text:
            return ""

        return await self._map_reduce_synthesize(query, summaries_text)

    async def local_search(self, query: str, user_id: str) -> str:
        """엔티티 임베딩 검색 → KuzuDB 2-hop 탐색 → 관계 컨텍스트 반환."""
        embedding = await self.vector_repo.embed_query(query)
        if not embedding:
            # 임베딩 없으면 키워드 기반 폴백
            return await self._fallback_keyword_graph(query, user_id)

        # 1. 엔티티 의미 유사도 검색
        top_entities = await asyncio.to_thread(self._search_entities, embedding, user_id)
        if not top_entities:
            return await self._fallback_keyword_graph(query, user_id)

        entity_names = [e["name"] for e in top_entities]

        # 2. KuzuDB 2-hop 이웃 탐색
        neighborhood = await self.mindmap_repo.get_entity_neighborhood(
            entity_names, user_id, hops=LOCAL_NEIGHBORHOOD_HOPS
        )

        if not neighborhood and not top_entities:
            return ""

        # 3. 결과 포맷
        graph_lines = []
        for e in top_entities[:5]:
            graph_lines.append(
                f"- {e['name']} ({e.get('entity_type', 'Concept')}) [유사도: {e.get('similarity', 0):.2f}]"
            )
        for rel in neighborhood[:12]:
            graph_lines.append(
                f"  → {rel.get('name', '')} ({rel.get('entity_type', '')})"
                f" via {rel.get('rel_type', 'RELATED_TO')} (depth={rel.get('hop', 1)})"
            )

        if not graph_lines:
            return ""

        graph_info = "\n".join(graph_lines)
        return await self._local_context_summarize(query, graph_info)

    # ------------------------------------------------------------------
    # 쿼리 분류
    # ------------------------------------------------------------------

    def _classify_query(self, query: str) -> str:
        """'global' | 'local' 반환.

        - 쿼리가 길거나 전체/개요 키워드 포함 → global
        - 짧고 구체적 → local
        """
        q_lower = query.lower()
        words = set(q_lower.split())
        # 1자 신호(다/총/왜)는 exact word match로 오탐 방지, 나머지는 활용형 포함 substring match
        short_signals = {s for s in GLOBAL_QUERY_SIGNALS if len(s) <= 1}
        long_signals = {s for s in GLOBAL_QUERY_SIGNALS if len(s) >= 2}
        if (words & short_signals) or any(sig in q_lower for sig in long_signals):
            return "global"
        if len(query) > 60:
            return "global"
        return "local"

    # ------------------------------------------------------------------
    # Supabase 벡터 검색 (동기, to_thread에서 호출)
    # ------------------------------------------------------------------

    def _search_communities(self, embedding: list[float], user_id: str, level: int) -> list[dict]:
        """match_graph_communities RPC 호출."""
        try:
            response = self.db.rpc(
                "match_graph_communities",
                {
                    "query_embedding": embedding,
                    "p_user_id": user_id,
                    "p_level": level,
                    "match_count": MATCH_TOP_K_COMMUNITIES,
                    "similarity_threshold": 0.4,
                },
            ).execute()
            return response.data or []
        except Exception:
            logger.exception("match_graph_communities RPC 실패")
            return []

    def _search_entities(self, embedding: list[float], user_id: str) -> list[dict]:
        """match_graph_entities RPC 호출."""
        try:
            response = self.db.rpc(
                "match_graph_entities",
                {
                    "query_embedding": embedding,
                    "p_user_id": user_id,
                    "match_count": MATCH_TOP_K_ENTITIES,
                    "similarity_threshold": 0.45,
                },
            ).execute()
            return response.data or []
        except Exception:
            logger.exception("match_graph_entities RPC 실패")
            return []

    # ------------------------------------------------------------------
    # LLM 합성
    # ------------------------------------------------------------------

    async def _map_reduce_synthesize(self, query: str, summaries_text: str) -> str:
        """커뮤니티 요약 → LLM 최종 합성."""
        try:
            llm = get_analytical_llm()
            prompt = MAP_REDUCE_PROMPT.format(query=query, summaries=summaries_text)
            response = await llm.ainvoke(
                [SystemMessage(content="당신은 지식 그래프 분석 AI입니다."), HumanMessage(content=prompt)]
            )
            return response.content.strip()
        except Exception:
            logger.warning("Global search LLM 합성 실패")
            return summaries_text[:500]

    async def _local_context_summarize(self, query: str, graph_info: str) -> str:
        """그래프 이웃 정보 → LLM 맥락 요약."""
        try:
            llm = get_analytical_llm()
            prompt = LOCAL_CONTEXT_PROMPT.format(query=query, graph_info=graph_info)
            response = await llm.ainvoke(
                [SystemMessage(content="당신은 지식 그래프 분석 AI입니다."), HumanMessage(content=prompt)]
            )
            return response.content.strip()
        except Exception:
            logger.warning("Local search LLM 요약 실패")
            return graph_info[:400]

    # ------------------------------------------------------------------
    # 폴백 (임베딩 없을 때)
    # ------------------------------------------------------------------

    async def _fallback_keyword_graph(self, query: str, user_id: str) -> str:
        """임베딩 없을 때 키워드 기반 KuzuDB 검색으로 폴백."""
        keywords = [w for w in query.split() if len(w) >= 2][:3]
        entity_names = []
        for kw in keywords:
            matched = await self.mindmap_repo.search_entities_by_name(kw, user_id)
            entity_names.extend(e["name"] for e in matched[:3])
        if not entity_names:
            return ""
        neighborhood = await self.mindmap_repo.get_entity_neighborhood(entity_names, user_id)
        lines = [f"- {r['name']} ({r.get('entity_type', '')})" for r in neighborhood[:10]]
        return "\n".join(lines)

    async def _fallback_keyword_community(self, query: str, user_id: str) -> str:
        """임베딩 없을 때 커뮤니티 키워드 매칭으로 폴백."""
        try:
            response = await asyncio.to_thread(
                lambda: self.db.table("graph_communities")
                .select("entities, summary")
                .eq("user_id", user_id)
                .eq("level", GLOBAL_COMMUNITY_LEVEL)
                .limit(20)
                .execute()
            )
            rows = response.data or []
        except Exception:
            return ""

        query_words = {w.lower() for w in query.split() if len(w) >= 2}
        relevant = []
        for row in rows:
            entity_words = {e.lower() for e in (row.get("entities") or [])}
            if query_words & entity_words and row.get("summary"):
                relevant.append(row["summary"])

        return "\n".join(f"- {s}" for s in relevant[:3])
