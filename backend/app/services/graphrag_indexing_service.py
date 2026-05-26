"""GraphRAG 인덱싱 서비스.

KuzuDB 엣지 → networkx 그래프 → Louvain 3-레벨 커뮤니티 감지
→ LLM 요약 + 임베딩 → Supabase graph_communities / graph_entities 저장.

호출 시점: POST /mindmap/reindex (수동), 또는 대규모 스크랩 저장 후 백그라운드.
"""

import asyncio
import logging
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from supabase import Client

from app.config.llm import get_analytical_llm
from app.repositories.protocols.mindmap_repository_protocol import MindmapRepositoryProtocol
from app.repositories.protocols.vector_repository_protocol import VectorRepositoryProtocol

logger = logging.getLogger(__name__)

# Louvain 해상도 레벨: 낮을수록 큰 커뮤니티(거칠음)
LOUVAIN_RESOLUTIONS = {0: 0.3, 1: 1.0, 2: 3.0}

# 커뮤니티 LLM 요약 설정
MAX_ENTITIES_PER_SUMMARY = 15
MAX_RELATIONS_PER_SUMMARY = 12
MAX_COMMUNITIES_TO_INDEX = 50  # 레벨당 최대 인덱싱 커뮤니티 수
MIN_COMMUNITY_SIZE = 2

COMMUNITY_SUMMARY_PROMPT = """You are summarizing a knowledge cluster from a user's personal memory graph.

Given entities and their relationships, write a 2-3 sentence summary capturing:
1. The main theme or topic
2. Key relationships (especially SUPPORTS, CONTRADICTS, LEADS_TO, CREATED_BY, RELATED_TO)
3. Why this cluster is meaningful

Output: A concise 2-3 sentence summary in Korean suitable as retrieval context for an AI assistant.

Entities: {entities}
Relations: {relations}
"""


class GraphRAGIndexingService:
    """Louvain 커뮤니티 감지 + LLM 요약 + 임베딩 → Supabase 저장."""

    def __init__(
        self,
        mindmap_repo: MindmapRepositoryProtocol,
        vector_repo: VectorRepositoryProtocol,
        db: Client,
    ):
        self.mindmap_repo = mindmap_repo
        self.vector_repo = vector_repo
        self.db = db

    # ------------------------------------------------------------------
    # 공개 인터페이스
    # ------------------------------------------------------------------

    async def reindex(self, user_id: str) -> dict:
        """사용자 그래프 전체 재인덱싱. 소요 시간이 길어 백그라운드 실행 권장."""
        edges = await self.mindmap_repo.get_all_edges(user_id)
        if not edges:
            return {"ok": True, "communities": 0, "entities": 0, "message": "그래프 데이터 없음"}

        # 1. networkx 그래프 구성
        graph = self._build_networkx_graph(edges)

        # 2. Louvain 3-레벨 커뮤니티 감지
        level_communities = self._detect_louvain_communities(graph)

        # 3. 레벨별 커뮤니티 요약 + 임베딩 저장
        total_communities = 0
        for level, communities in level_communities.items():
            saved = await self._index_communities(user_id, level, communities, edges)
            total_communities += saved

        # 4. 엔티티 임베딩 저장
        entity_count = await self._index_entities(user_id, edges)

        logger.info(
            "GraphRAG 인덱싱 완료: user=%s, communities=%d, entities=%d",
            user_id,
            total_communities,
            entity_count,
        )
        return {
            "ok": True,
            "communities": total_communities,
            "entities": entity_count,
            "message": f"커뮤니티 {total_communities}개, 엔티티 {entity_count}개 인덱싱 완료",
        }

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    @staticmethod
    def _build_networkx_graph(edges: list[dict]):
        """KuzuDB 엣지 목록에서 networkx 무향 그래프 구성."""
        try:
            import networkx as nx
        except ImportError:
            logger.error("networkx 미설치. requirements.txt에 networkx>=3.0 추가 필요.")
            raise

        G = nx.Graph()
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src and tgt and src != tgt:
                if G.has_edge(src, tgt):
                    G[src][tgt]["weight"] = G[src][tgt].get("weight", 1) + 1
                else:
                    G.add_edge(src, tgt, weight=1)
                # 노드 타입 저장
                if src not in G.nodes or "type" not in G.nodes[src]:
                    G.nodes[src]["type"] = edge.get("source_type", "Concept")
                if tgt not in G.nodes or "type" not in G.nodes[tgt]:
                    G.nodes[tgt]["type"] = edge.get("target_type", "Concept")
        return G

    @staticmethod
    def _detect_louvain_communities(graph) -> dict[int, dict[int, list[str]]]:
        """3-레벨 Louvain 커뮤니티 감지.

        Returns:
            {level: {community_id: [entity_name, ...]}}
        """
        try:
            import community as community_louvain
        except ImportError:
            logger.error("python-louvain 미설치. requirements.txt에 python-louvain>=0.16 추가 필요.")
            raise

        if graph.number_of_nodes() < MIN_COMMUNITY_SIZE:
            return {}

        result: dict[int, dict[int, list[str]]] = {}
        for level, resolution in LOUVAIN_RESOLUTIONS.items():
            try:
                partition = community_louvain.best_partition(graph, resolution=resolution)
                communities: dict[int, list[str]] = {}
                for node, cid in partition.items():
                    communities.setdefault(cid, []).append(node)
                # 최소 크기 이상만 유지
                communities = {
                    cid: members for cid, members in communities.items() if len(members) >= MIN_COMMUNITY_SIZE
                }
                result[level] = communities
                logger.info(
                    "Louvain level=%d (resolution=%.1f): %d communities",
                    level,
                    resolution,
                    len(communities),
                )
            except Exception:
                logger.exception("Louvain level=%d 감지 실패", level)
                result[level] = {}

        return result

    async def _index_communities(
        self,
        user_id: str,
        level: int,
        communities: dict[int, list[str]],
        all_edges: list[dict],
    ) -> int:
        """단일 레벨의 커뮤니티들을 LLM 요약 + 임베딩 후 Supabase에 저장."""
        edge_index: dict[frozenset, str] = {}
        for e in all_edges:
            key = frozenset([e.get("source", ""), e.get("target", "")])
            edge_index[key] = e.get("rel_type", "RELATED_TO")

        saved = 0
        top_communities = sorted(communities.items(), key=lambda x: len(x[1]), reverse=True)[:MAX_COMMUNITIES_TO_INDEX]

        for cid, members in top_communities:
            try:
                summary = await self._generate_summary(members, all_edges)
                embedding = await self.vector_repo.embed_query(summary) if summary else None

                row = {
                    "user_id": user_id,
                    "level": level,
                    "community_id": cid,
                    "entities": members[:MAX_ENTITIES_PER_SUMMARY],
                    "entity_count": len(members),
                    "summary": summary,
                    "summary_embedding": embedding,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                await asyncio.to_thread(self._upsert_community, row)
                saved += 1
            except Exception:
                logger.exception("커뮤니티 저장 실패: level=%d, cid=%d", level, cid)

        return saved

    def _upsert_community(self, row: dict) -> None:
        """graph_communities upsert (동기, to_thread에서 호출)."""
        self.db.table("graph_communities").upsert(row, on_conflict="user_id,level,community_id").execute()

    async def _generate_summary(self, members: list[str], all_edges: list[dict]) -> str:
        """커뮤니티 내부 엔티티+관계 → LLM 2-3문장 요약."""
        member_set = set(members)
        internal_edges = [e for e in all_edges if e.get("source") in member_set and e.get("target") in member_set][
            :MAX_RELATIONS_PER_SUMMARY
        ]

        entities_str = ", ".join(members[:MAX_ENTITIES_PER_SUMMARY])
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
            logger.warning("커뮤니티 요약 LLM 실패: entities=%s", members[:3])
            return f"{members[0]} 외 {len(members) - 1}개 관련 지식 클러스터"

    async def _index_entities(self, user_id: str, edges: list[dict]) -> int:
        """엔티티 이름+타입으로 설명 텍스트 구성 후 임베딩 → graph_entities 저장."""
        # 엔티티 목록 + 타입 수집
        entity_map: dict[str, str] = {}
        for e in edges:
            src, src_type = e.get("source", ""), e.get("source_type", "Concept")
            tgt, tgt_type = e.get("target", ""), e.get("target_type", "Concept")
            if src:
                entity_map.setdefault(src, src_type)
            if tgt:
                entity_map.setdefault(tgt, tgt_type)

        if not entity_map:
            return 0

        # 엔티티당 연결된 관계 텍스트 구성 (임베딩 품질 향상)
        entity_relations: dict[str, list[str]] = {name: [] for name in entity_map}
        for e in edges:
            src, tgt = e.get("source", ""), e.get("target", "")
            rel = e.get("rel_type", "RELATED_TO")
            if src in entity_relations:
                entity_relations[src].append(f"{rel} {tgt}")
            if tgt in entity_relations:
                entity_relations[tgt].append(f"{src} {rel}")

        saved = 0
        entity_items = list(entity_map.items())

        # 배치 임베딩 (최대 100개씩)
        batch_size = 100
        for i in range(0, len(entity_items), batch_size):
            batch = entity_items[i : i + batch_size]
            texts = []
            for name, etype in batch:
                rels = entity_relations.get(name, [])[:5]
                desc = f"{name} ({etype})"
                if rels:
                    desc += ": " + ", ".join(rels)
                texts.append(desc)

            try:
                embeddings = await self.vector_repo.embed_documents(texts)
                for (name, etype), emb, text in zip(batch, embeddings, texts, strict=False):
                    row = {
                        "user_id": user_id,
                        "name": name,
                        "entity_type": etype,
                        "description": text,
                        "embedding": emb if emb else None,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                    await asyncio.to_thread(self._upsert_entity, row)
                    saved += 1
            except Exception:
                logger.exception("엔티티 배치 임베딩 저장 실패: batch=%d", i)

        return saved

    def _upsert_entity(self, row: dict) -> None:
        """graph_entities upsert (동기, to_thread에서 호출)."""
        self.db.table("graph_entities").upsert(row, on_conflict="user_id,name").execute()
