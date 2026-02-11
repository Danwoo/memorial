from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.utils import parse_iso_datetime


class SearchService:
    """시맨틱 검색 및 추천 비즈니스 로직."""

    def __init__(self, vector_repo: VectorRepository, memory_repo: MemoryRepository | None = None):
        self.vector_repo = vector_repo
        self.memory_repo = memory_repo

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
        """필터링 지원 시맨틱 검색. 검색 결과와 적용된 필터 반환."""
        filters: dict[str, Any] = {"user_id": str(user_id)}
        filters_applied: dict[str, Any] = {}

        if source_type:
            filters["source_type"] = source_type
            filters_applied["source_type"] = source_type

        if days:
            filters_applied["days"] = days

        if tags:
            filters_applied["tags"] = tags

        # 필터링 여유분을 고려하여 2배 조회
        results = await self.vector_repo.similarity_search(
            query=query,
            limit=limit * 2,
            threshold=threshold,
            filters=filters,
        )

        filtered_results = []
        now = datetime.now(UTC)

        for r in results:
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
                memory_tags = r.get("tags") or []
                if not any(t in memory_tags for t in tags):
                    continue

            filtered_results.append(
                {
                    "id": str(r.get("id", "")),
                    "title": r.get("title", "Untitled"),
                    "content": r.get("content", "")[:500],
                    "summary": r.get("summary"),
                    "source_type": r.get("source_type", "NOTE"),
                    "similarity": r.get("similarity", 0),
                    "created_at": r.get("created_at"),
                    "tags": r.get("tags"),
                }
            )

            if len(filtered_results) >= limit:
                break

        return {
            "query": query,
            "results": filtered_results,
            "total": len(filtered_results),
            "filters_applied": filters_applied,
        }

    async def get_related_memories(
        self,
        user_id: UUID,
        memory_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """특정 Memory와 유사한 Memory 목록 조회."""
        if not self.memory_repo:
            return []

        source = await self.memory_repo.get_by_id(UUID(memory_id), user_id)
        if not source:
            return []

        query_text = source.content or source.title

        similar = await self.vector_repo.similarity_search(
            query=query_text,
            limit=limit + 1,
            threshold=0.3,
            filters={"user_id": str(user_id)},
        )

        # 원본 Memory 제외
        related = []
        for item in similar:
            if str(item.get("id")) != memory_id:
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
