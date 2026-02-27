import logging
from typing import Any
from uuid import UUID

from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.vector_repository import VectorRepository
from app.services.korean_tokenizer import tokenize, tokens_to_tsvector_input

logger = logging.getLogger(__name__)

# Weighted RRF 파라미터 (tune_hybrid_params.py 최적화 결과)
RRF_K = 10
WEIGHT_DENSE = 1.0
WEIGHT_SPARSE = 1.0
WEIGHT_GRAPH = 0.5

# 기본 검색 설정
DEFAULT_DENSE_LIMIT = 20
DEFAULT_SPARSE_LIMIT = 20
DEFAULT_GRAPH_LIMIT = 10


class HybridSearchService:
    """3축 하이브리드 검색 서비스 (Dense + Sparse + Graph).

    Weighted Reciprocal Rank Fusion (RRF)으로 3개 검색 결과를 통합한다.
    각 축은 독립적으로 동작하며, 실패 시 나머지 축으로 graceful degradation한다.
    """

    def __init__(
        self,
        vector_repo: VectorRepository,
        mindmap_repo: MindmapRepository | None = None,
        scrap_repo: ScrapRepository | None = None,
    ):
        self.vector_repo = vector_repo
        self.mindmap_repo = mindmap_repo
        self.scrap_repo = scrap_repo

    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 10,
        dense_threshold: float = 0.0,
        enable_sparse: bool = True,
        enable_graph: bool = True,
    ) -> list[dict[str, Any]]:
        """3축 하이브리드 검색 실행.

        Args:
            user_id: 사용자 ID
            query: 검색 쿼리
            limit: 최종 반환 결과 수
            dense_threshold: 벡터 검색 유사도 임계값 (0.0이면 전체)
            enable_sparse: sparse 검색 활성화 여부
            enable_graph: graph 검색 활성화 여부

        Returns:
            RRF 점수 기준 정렬된 스크랩 리스트
        """
        user_id_str = str(user_id)

        # 1. Dense vector search
        dense_results = await self._dense_search(query, user_id_str, dense_threshold)

        # 2. Sparse keyword search (실패 시 dense 결과만 사용)
        sparse_results = []
        if enable_sparse:
            try:
                sparse_results = await self._sparse_search(query, user_id_str)
            except Exception:
                logger.warning("Sparse 검색 실패, dense 결과만 사용", exc_info=True)

        # 3. Graph-based search
        graph_results = []
        if enable_graph and self.mindmap_repo:
            graph_results = await self._graph_search(query, user_id_str)

        logger.info(
            "하이브리드 검색 축별 결과 — dense=%d, sparse=%d, graph=%d (query=%r)",
            len(dense_results),
            len(sparse_results),
            len(graph_results),
            query[:50],
        )

        # 4. Weighted RRF fusion
        fused = self._rrf_fusion(dense_results, sparse_results, graph_results)

        # 5. 메모리 상세 정보 보강 (graph 결과는 ID만 있으므로)
        enriched = await self._enrich_results(fused, user_id_str, limit)

        return enriched

    async def _dense_search(self, query: str, user_id: str, threshold: float) -> list[dict[str, Any]]:
        """Dense vector search 실행."""
        try:
            results = await self.vector_repo.similarity_search(
                query=query,
                limit=DEFAULT_DENSE_LIMIT,
                threshold=threshold,
                filters={"user_id": user_id},
            )
            return [{"id": str(r.get("id", "")), "similarity": r.get("similarity", 0), **r} for r in results]
        except Exception:
            logger.exception("Dense search 실패")
            return []

    async def _sparse_search(self, query: str, user_id: str) -> list[dict[str, Any]]:
        """Sparse keyword search 실행. 쿼리를 kiwipiepy로 토큰화 후 tsvector 검색."""
        try:
            tokens = tokenize(query)
            token_string = tokens_to_tsvector_input(tokens)
            if not token_string:
                return []

            results = await self.vector_repo.sparse_search(
                query_tokens=token_string,
                user_id=user_id,
                limit=DEFAULT_SPARSE_LIMIT,
            )
            return [{"id": str(r.get("id", "")), "rank": r.get("rank", 0), **r} for r in results]
        except Exception:
            logger.exception("Sparse search 실패")
            return []

    async def _graph_search(self, query: str, user_id: str) -> list[dict[str, Any]]:
        """Graph-based search 실행. 엔티티 이름 매칭 → 스크랩 역탐색."""
        try:
            results = await self.mindmap_repo.search_memories_via_graph(
                query=query,
                user_id=user_id,
                limit=DEFAULT_GRAPH_LIMIT,
            )
            return [{"id": r.get("scrap_id", ""), "graph_score": r.get("graph_score", 0)} for r in results]
        except Exception:
            logger.exception("Graph search 실패")
            return []

    def _rrf_fusion(
        self,
        dense: list[dict],
        sparse: list[dict],
        graph: list[dict],
    ) -> list[dict[str, Any]]:
        """Weighted Reciprocal Rank Fusion.

        각 축의 순위를 기반으로 통합 점수를 계산한다.
        score(d) = w_dense / (k + rank_dense(d))
                 + w_sparse / (k + rank_sparse(d))
                 + w_graph / (k + rank_graph(d))
        """
        scores: dict[str, float] = {}
        sources: dict[str, set[str]] = {}  # 어떤 축에서 검색되었는지 추적

        # Dense 기여
        for rank, item in enumerate(dense):
            doc_id = item.get("id", "")
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0) + WEIGHT_DENSE / (RRF_K + rank + 1)
            sources.setdefault(doc_id, set()).add("dense")

        # Sparse 기여
        for rank, item in enumerate(sparse):
            doc_id = item.get("id", "")
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0) + WEIGHT_SPARSE / (RRF_K + rank + 1)
            sources.setdefault(doc_id, set()).add("sparse")

        # Graph 기여
        for rank, item in enumerate(graph):
            doc_id = item.get("id", "")
            if not doc_id:
                continue
            scores[doc_id] = scores.get(doc_id, 0) + WEIGHT_GRAPH / (RRF_K + rank + 1)
            sources.setdefault(doc_id, set()).add("graph")

        # 점수순 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 원본 데이터 매핑 (dense/sparse 결과에서 메타데이터 가져오기)
        all_items: dict[str, dict] = {}
        for item in dense:
            doc_id = item.get("id", "")
            if doc_id:
                all_items[doc_id] = item
        for item in sparse:
            doc_id = item.get("id", "")
            if doc_id and doc_id not in all_items:
                all_items[doc_id] = item

        results = []
        for doc_id in sorted_ids:
            base = all_items.get(doc_id, {"id": doc_id})
            results.append(
                {
                    **base,
                    "id": doc_id,
                    "hybrid_score": scores[doc_id],
                    "search_sources": list(sources.get(doc_id, set())),
                }
            )

        return results

    async def _enrich_results(
        self,
        fused: list[dict],
        user_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """RRF 결과에 스크랩 상세 정보 보강. graph-only 결과는 DB 조회 필요."""
        if not self.scrap_repo:
            return fused[:limit]

        enriched = []
        for item in fused[:limit]:
            # dense/sparse에서 이미 title/content가 있으면 그대로 사용
            if item.get("title"):
                enriched.append(item)
                continue

            # graph-only 결과: DB에서 조회
            try:
                scrap = await self.scrap_repo.get_by_id(UUID(item["id"]), UUID(user_id))
                if scrap:
                    enriched.append(
                        {
                            **item,
                            "title": scrap.title,
                            "content": scrap.content,
                            "summary": scrap.summary,
                            "source_type": scrap.source_type,
                            "created_at": scrap.created_at.isoformat() if scrap.created_at else None,
                            "tags": scrap.tags,
                        }
                    )
                else:
                    enriched.append(item)
            except Exception:
                enriched.append(item)

        return enriched
