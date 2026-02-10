"""
Search Service
Business logic for semantic search and recommendations
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.utils import parse_iso_datetime


class SearchService:
    """Service for search business logic"""

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
        """
        Advanced semantic search with filtering.
        Returns search results with applied filters.
        """
        # Build filters for vector search
        filters: dict[str, Any] = {"user_id": str(user_id)}
        filters_applied: dict[str, Any] = {}

        if source_type:
            filters["source_type"] = source_type
            filters_applied["source_type"] = source_type

        if days:
            filters_applied["days"] = days

        if tags:
            filters_applied["tags"] = tags

        # Perform vector search (get more results for filtering)
        results = await self.vector_repo.similarity_search(
            query=query,
            limit=limit * 2,
            threshold=threshold,
            filters=filters,
        )

        # Apply additional filters
        filtered_results = []
        now = datetime.now(UTC)

        for r in results:
            # Time filter
            if days:
                created_at_str = r.get("created_at")
                if created_at_str:
                    try:
                        created_at = parse_iso_datetime(created_at_str)
                        if (now - created_at) > timedelta(days=days):
                            continue
                    except Exception:
                        pass

            # Tag filter
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
        """
        Get memories related to a specific memory.
        Uses the memory's content to find similar items.
        """
        if not self.memory_repo:
            return []

        # Fetch the source memory's content for vector similarity
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

        # Filter out the source memory
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
