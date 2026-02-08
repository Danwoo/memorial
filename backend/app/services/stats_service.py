"""
Stats Service
Business logic for dashboard statistics
"""
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.repositories.stats_repository import StatsRepository
from app.schemas.stats import (
    ActivityData,
    OverviewStats,
    SourceStats,
    StatsOverviewResponse,
    TagStats,
    TimelineGroup,
)


class StatsService:
    """Service for statistics business logic"""

    def __init__(self, stats_repo: StatsRepository):
        self.stats_repo = stats_repo

    async def get_overview(self, user_id: UUID) -> StatsOverviewResponse:
        """Get complete dashboard statistics."""
        memories = await self.stats_repo.get_all_memories(user_id)

        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        total = len(memories)
        weekly_count = 0
        monthly_count = 0
        day_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}

        for memory in memories:
            created_at_str = memory.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )

                    if created_at >= week_ago:
                        weekly_count += 1
                    if created_at >= month_ago:
                        monthly_count += 1

                    day_key = created_at.strftime("%Y-%m-%d")
                    day_counts[day_key] = day_counts.get(day_key, 0) + 1
                except Exception:
                    pass

            # Count sources
            source_type = memory.get("source_type", "UNKNOWN")
            source_counts[source_type] = source_counts.get(source_type, 0) + 1

            # Count tags
            for tag in memory.get("tags") or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Find most active day
        most_active_day = None
        if day_counts:
            most_active_day = max(day_counts, key=day_counts.get)

        # Prepare response
        overview = OverviewStats(
            total_memories=total,
            total_this_week=weekly_count,
            total_this_month=monthly_count,
            most_active_day=most_active_day
        )

        # Recent activity (last 30 days)
        recent_activity = []
        for i in range(30):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            recent_activity.append(ActivityData(
                date=date,
                count=day_counts.get(date, 0)
            ))
        recent_activity.reverse()

        # Source stats
        sources = [
            SourceStats(
                source_type=st,
                count=cnt,
                percentage=cnt / total * 100 if total > 0 else 0
            )
            for st, cnt in source_counts.items()
        ]

        # Top tags
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_tags = [TagStats(tag=tag, count=cnt) for tag, cnt in sorted_tags]

        return StatsOverviewResponse(
            overview=overview,
            recent_activity=recent_activity,
            sources=sources,
            top_tags=top_tags
        )

    async def get_activity(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> list[ActivityData]:
        """Get daily activity data for a range."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)

        memories = await self.stats_repo.get_memories_in_range(user_id, start_date, now)

        day_counts: dict[str, int] = {}
        for memory in memories:
            created_at_str = memory.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    day_key = created_at.strftime("%Y-%m-%d")
                    day_counts[day_key] = day_counts.get(day_key, 0) + 1
                except Exception:
                    pass

        result = []
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            result.append(ActivityData(date=date, count=day_counts.get(date, 0)))

        result.reverse()
        return result

    async def get_timeline(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get memories grouped by date for timeline view."""
        memories = await self.stats_repo.get_memories_by_date(user_id, page, limit)

        grouped: dict[str, list] = {}
        for memory in memories:
            created_at_str = memory.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    day_key = created_at.strftime("%Y-%m-%d")
                    if day_key not in grouped:
                        grouped[day_key] = []
                    grouped[day_key].append(memory)
                except Exception:
                    pass

        timeline = [
            TimelineGroup(date=date, memories=mems)
            for date, mems in sorted(grouped.items(), reverse=True)
        ]

        return {
            "page": page,
            "limit": limit,
            "timeline": timeline,
            "has_more": len(memories) == limit
        }
