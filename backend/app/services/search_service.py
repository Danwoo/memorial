import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.vector_repository import VectorRepository
from app.services.hybrid_search_service import HybridSearchService
from app.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

SEARCH_CONTENT_PREVIEW_LENGTH = 500
SEARCH_OVERSAMPLE_FACTOR = 2
RELATED_SIMILARITY_THRESHOLD = 0.3


class SearchService:
    """시맨틱 검색 및 추천 비즈니스 로직. 하이브리드 검색을 기본 사용."""

    def __init__(
        self,
        vector_repo: VectorRepository,
        scrap_repo: ScrapRepository | None = None,
        mindmap_repo: MindmapRepository | None = None,
        *,
        hybrid_search: HybridSearchService | None = None,
    ):
        self.vector_repo = vector_repo
        self.scrap_repo = scrap_repo
        self.hybrid = hybrid_search or HybridSearchService(vector_repo, mindmap_repo, scrap_repo)

    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.3,
        source_type: str | None = None,
        days: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """하이브리드 검색 (Dense + Sparse + Graph + RRF)."""
        filters_applied: dict[str, Any] = {}

        if source_type:
            filters_applied["source_type"] = source_type
        if days:
            filters_applied["days"] = days
        if tags:
            filters_applied["tags"] = tags

        # 하이브리드 검색 실행 (threshold=0.0으로 전체 결과 가져온 후 클라이언트 필터링)
        raw_results = await self.hybrid.search(
            user_id=user_id,
            query=query,
            limit=limit * SEARCH_OVERSAMPLE_FACTOR,
            dense_threshold=0.0,
        )

        logger.info("검색 raw 결과: %d건 (query=%r)", len(raw_results), query[:50])

        # 클라이언트 측 필터링
        filtered_results = []
        now = datetime.now(UTC)

        for r in raw_results:
            # source_type 필터
            if source_type and r.get("source_type") != source_type:
                continue

            # 기간 필터
            if days:
                created_at_str = r.get("created_at")
                if created_at_str:
                    try:
                        created_at = parse_iso_datetime(created_at_str)
                        if (now - created_at) > timedelta(days=days):
                            continue
                    except Exception:
                        pass

            # 태그 필터
            if tags:
                scrap_tags = r.get("tags") or []
                if not any(t in scrap_tags for t in tags):
                    continue

            filtered_results.append(
                {
                    "id": str(r.get("id", "")),
                    "title": r.get("title", "Untitled"),
                    "content": (r.get("content") or "")[:SEARCH_CONTENT_PREVIEW_LENGTH],
                    "summary": r.get("summary"),
                    "source_type": r.get("source_type", "NOTE"),
                    "similarity": r.get("similarity", r.get("hybrid_score", 0)),
                    "hybrid_score": r.get("hybrid_score", 0),
                    "search_sources": r.get("search_sources", []),
                    "created_at": r.get("created_at"),
                    "tags": r.get("tags"),
                }
            )

            if len(filtered_results) >= limit:
                break

        logger.info("검색 필터링 후: %d건 (filters=%s)", len(filtered_results), filters_applied)

        return {
            "query": query,
            "results": filtered_results,
            "total": len(filtered_results),
            "filters_applied": filters_applied,
        }

    async def get_related_scraps(
        self,
        user_id: UUID,
        scrap_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """특정 Scrap과 유사한 Scrap 목록 조회."""
        if not self.scrap_repo:
            return []

        source = await self.scrap_repo.get_by_id(UUID(scrap_id), user_id)
        if not source:
            return []

        query_text = source.content or source.title

        similar = await self.vector_repo.similarity_search(
            query=query_text,
            limit=limit + 1,
            threshold=RELATED_SIMILARITY_THRESHOLD,
            filters={"user_id": str(user_id)},
        )

        related = []
        for item in similar:
            if str(item.get("id")) != scrap_id:
                related.append(
                    {
                        "id": str(item.get("id", "")),
                        "title": item.get("title", "Untitled"),
                        "similarity": item.get("similarity", 0),
                    }
                )
            if len(related) >= limit:
                break

        return related
