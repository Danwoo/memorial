import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.repositories.graph_repository import GraphRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.stats_repository import StatsRepository
from app.schemas.insight_schema import DailyInsight, DailyInsightsResponse
from app.utils.cache import insights_cache

logger = logging.getLogger(__name__)


class InsightService:
    """일일 인사이트 생성 서비스. 규칙 기반 우선, 비용 절감."""

    def __init__(
        self,
        stats_repo: StatsRepository,
        graph_repo: GraphRepository,
        journal_repo: JournalRepository,
    ):
        self.stats_repo = stats_repo
        self.graph_repo = graph_repo
        self.journal_repo = journal_repo

    async def get_daily_insights(self, user_id: str) -> DailyInsightsResponse:
        """규칙 기반 일일 인사이트 최대 3개 생성."""
        cache_key = f"daily_insights:{user_id}"
        cached = insights_cache.get(cache_key)
        if cached is not None:
            return cached

        insights: list[DailyInsight] = []
        uid = UUID(user_id)
        now = datetime.now(UTC)

        # 1. 패턴 감지: 이번 주 집중 주제
        try:
            week_start = now - timedelta(days=7)
            week_memories = await self.stats_repo.get_memories_in_range(uid, week_start, now)
            if week_memories:
                tag_counter: Counter[str] = Counter()
                for mem in week_memories:
                    for tag in mem.get("tags") or []:
                        tag_counter[tag] += 1
                if tag_counter:
                    top_tag, top_count = tag_counter.most_common(1)[0]
                    if top_count >= 2:
                        insights.append(
                            DailyInsight(
                                type="pattern",
                                icon="TrendingUp",
                                title=f"이번 주 '{top_tag}' 집중",
                                description=f"최근 7일간 '{top_tag}' 관련 기억이 {top_count}개 기록되었어요.",
                                cta_label="관련 기억 보기",
                                cta_path="/memories",
                            )
                        )
        except Exception:
            logger.warning("패턴 감지 인사이트 생성 실패")

        # 2. 연결 발견: 고립 노드 발견
        try:
            if self.graph_repo.is_connected:
                orphans = await self.graph_repo.get_orphan_entities(user_id)
                if len(orphans) >= 3:
                    sample = orphans[0]
                    insights.append(
                        DailyInsight(
                            type="connection",
                            icon="Link2",
                            title=f"'{sample['name']}' 외 {len(orphans) - 1}개 연결 가능",
                            description="아직 다른 개념과 연결되지 않은 엔티티가 있어요. 지식 그래프에서 연결해보세요.",
                            cta_label="그래프에서 보기",
                            cta_path="/graph",
                        )
                    )
        except Exception:
            logger.warning("연결 발견 인사이트 생성 실패")

        # 3. 행동 제안: 저널 미작성 알림
        try:
            three_days_ago = now - timedelta(days=3)
            recent_journals = await self.journal_repo.get_journals_in_range(
                uid,
                three_days_ago,
                now,
            )
            if not recent_journals:
                insights.append(
                    DailyInsight(
                        type="action",
                        icon="Pencil",
                        title="저널 작성 3일 이상 미작성",
                        description="최근 3일간 저널을 작성하지 않았어요. 오늘의 생각을 기록해보세요.",
                        cta_label="저널 쓰러 가기",
                        cta_path="/journal",
                    )
                )
        except Exception:
            logger.warning("행동 제안 인사이트 생성 실패")

        result = DailyInsightsResponse(insights=insights[:3])
        insights_cache.set(cache_key, result)
        return result
