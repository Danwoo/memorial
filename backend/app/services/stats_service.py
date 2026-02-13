import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.repositories.stats_repository import StatsRepository
from app.schemas.stats_schema import (
    ActivityData,
    OverviewStats,
    SourceStats,
    StatsOverviewResponse,
    StreakResponse,
    TagStats,
    TimelineGroup,
)
from app.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

OVERVIEW_ACTIVITY_DAYS = 30
TOP_TAGS_LIMIT = 10


def _count_by_day(memories: list[dict]) -> dict[str, int]:
    """메모리 목록에서 날짜별(YYYY-MM-DD) 카운트 집계."""
    day_counts: dict[str, int] = defaultdict(int)
    for memory in memories:
        created_at_str = memory.get("created_at", "")
        if not created_at_str:
            continue
        try:
            created_at = parse_iso_datetime(created_at_str)
            day_counts[created_at.strftime("%Y-%m-%d")] += 1
        except (ValueError, TypeError):
            pass
    return dict(day_counts)


def _build_activity_series(day_counts: dict[str, int], now: datetime, days: int) -> list[ActivityData]:
    """day_counts로부터 연속 날짜 ActivityData 시리즈 생성 (오래된 순)."""
    result = [
        ActivityData(
            date=(now - timedelta(days=i)).strftime("%Y-%m-%d"),
            count=day_counts.get((now - timedelta(days=i)).strftime("%Y-%m-%d"), 0),
        )
        for i in range(days)
    ]
    result.reverse()
    return result


class StatsService:
    """대시보드 통계 비즈니스 로직."""

    def __init__(self, stats_repo: StatsRepository):
        self.stats_repo = stats_repo

    async def get_overview(self, user_id: UUID) -> StatsOverviewResponse:
        """대시보드 전체 통계 조회."""
        memories = await self.stats_repo.get_all_memories(user_id)

        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=OVERVIEW_ACTIVITY_DAYS)

        total = len(memories)
        weekly_count = 0
        monthly_count = 0
        source_counts: dict[str, int] = defaultdict(int)
        tag_counts: dict[str, int] = defaultdict(int)

        for memory in memories:
            created_at_str = memory.get("created_at", "")
            if created_at_str:
                try:
                    created_at = parse_iso_datetime(created_at_str)
                    if created_at >= week_ago:
                        weekly_count += 1
                    if created_at >= month_ago:
                        monthly_count += 1
                except (ValueError, TypeError):
                    pass

            source_counts[memory.get("source_type", "UNKNOWN")] += 1
            for tag in memory.get("tags") or []:
                tag_counts[tag] += 1

        day_counts = _count_by_day(memories)
        most_active_day = max(day_counts, key=day_counts.get) if day_counts else None

        overview = OverviewStats(
            total_memories=total,
            total_this_week=weekly_count,
            total_this_month=monthly_count,
            most_active_day=most_active_day,
        )

        recent_activity = _build_activity_series(day_counts, now, OVERVIEW_ACTIVITY_DAYS)

        sources = [
            SourceStats(source_type=st, count=cnt, percentage=cnt / total * 100 if total > 0 else 0)
            for st, cnt in source_counts.items()
        ]

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:TOP_TAGS_LIMIT]
        top_tags = [TagStats(tag=tag, count=cnt) for tag, cnt in sorted_tags]

        return StatsOverviewResponse(
            overview=overview,
            recent_activity=recent_activity,
            sources=sources,
            top_tags=top_tags,
        )

    async def get_activity(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> list[ActivityData]:
        """지정 기간의 일별 활동 데이터 조회."""
        now = datetime.now(UTC)
        start_date = now - timedelta(days=days)

        memories = await self.stats_repo.get_memories_in_range(user_id, start_date, now)
        day_counts = _count_by_day(memories)
        return _build_activity_series(day_counts, now, days)

    async def get_timeline(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """타임라인 뷰용 날짜별 Memory 그룹 조회."""
        memories = await self.stats_repo.get_memories_by_date(user_id, page, limit)

        grouped: dict[str, list] = defaultdict(list)
        for memory in memories:
            created_at_str = memory.get("created_at", "")
            if not created_at_str:
                continue
            try:
                created_at = parse_iso_datetime(created_at_str)
                grouped[created_at.strftime("%Y-%m-%d")].append(memory)
            except (ValueError, TypeError):
                pass

        timeline = [TimelineGroup(date=date, memories=mems) for date, mems in sorted(grouped.items(), reverse=True)]

        return {"page": page, "limit": limit, "timeline": timeline, "has_more": len(memories) == limit}

    async def get_streak(self, user_id: UUID) -> StreakResponse:
        """활동 스트릭 계산 (메모리 + 저널 기준 연속 활동일)."""
        active_dates = await self.stats_repo.get_all_active_dates(user_id)
        if not active_dates:
            return StreakResponse(current_streak=0, longest_streak=0, total_active_days=0)

        sorted_dates = sorted(active_dates, reverse=True)
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # 현재 스트릭 계산 (오늘 또는 어제부터 역순으로)
        current_streak = 0
        check_date = datetime.strptime(today, "%Y-%m-%d")
        # 오늘 활동이 없으면 어제부터 확인
        if today not in active_dates:
            check_date -= timedelta(days=1)
        while check_date.strftime("%Y-%m-%d") in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

        # 최장 스트릭 계산
        longest_streak = 0
        streak = 0
        prev_date = None
        for date_str in sorted(active_dates):
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if prev_date and (d - prev_date).days == 1:
                streak += 1
            else:
                streak = 1
            longest_streak = max(longest_streak, streak)
            prev_date = d

        return StreakResponse(
            current_streak=current_streak,
            longest_streak=longest_streak,
            total_active_days=len(active_dates),
            last_active_date=sorted_dates[0] if sorted_dates else None,
        )
