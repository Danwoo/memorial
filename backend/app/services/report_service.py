import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.config.llm import get_analytical_llm
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.protocols.scrap_repository_protocol import ScrapRepositoryProtocol
from app.schemas.report_schema import ReportResponse, SourceDistribution, TopicDistribution
from app.utils.cache import report_cache

logger = logging.getLogger(__name__)


class ReportService:
    """주간/월간 AI 리포트 생성 서비스."""

    def __init__(self, calendar_repo: CalendarRepository, scrap_repo: ScrapRepositoryProtocol):
        self.calendar_repo = calendar_repo
        self.scrap_repo = scrap_repo

    async def get_weekly_report(self, user_id: UUID) -> ReportResponse:
        """최근 7일 AI 리포트."""
        cache_key = f"report:weekly:{user_id}"
        cached = report_cache.get(cache_key)
        if cached:
            return cached

        result = await self._generate_report(user_id, days=7, period="weekly")
        report_cache.set(cache_key, result)
        return result

    async def get_monthly_report(self, user_id: UUID) -> ReportResponse:
        """최근 30일 AI 리포트."""
        cache_key = f"report:monthly:{user_id}"
        cached = report_cache.get(cache_key)
        if cached:
            return cached

        result = await self._generate_report(user_id, days=30, period="monthly")
        report_cache.set(cache_key, result)
        return result

    async def _generate_report(self, user_id: UUID, days: int, period: str) -> ReportResponse:
        now = datetime.now(UTC)
        start = now - timedelta(days=days)
        end_date_str = now.strftime("%Y-%m-%d")
        start_date_str = start.strftime("%Y-%m-%d")

        memories = await self.calendar_repo.get_scraps_in_range(user_id, start, now)
        diary_count = await self._count_journals(user_id, start, now)

        # 주제 분포 (태그 기반)
        tag_counter: Counter[str] = Counter()
        source_counter: Counter[str] = Counter()
        titles: list[str] = []

        for mem in memories:
            tags = mem.get("tags") or []
            for tag in tags:
                tag_counter[tag] += 1
            source_counter[mem.get("source_type", "UNKNOWN")] += 1
            titles.append(mem.get("title", ""))

        total = len(memories)
        topic_dist = [
            TopicDistribution(topic=t, count=c, percentage=round(c / max(total, 1) * 100, 1))
            for t, c in tag_counter.most_common(10)
        ]
        source_dist = [
            SourceDistribution(source_type=s, count=c, percentage=round(c / max(total, 1) * 100, 1))
            for s, c in source_counter.most_common()
        ]

        # LLM 요약
        llm_summary = ""
        highlights: list[str] = []
        if total > 0:
            try:
                llm_summary, highlights = await self._generate_llm_summary(
                    period,
                    titles,
                    tag_counter,
                    total,
                    diary_count,
                )
            except Exception:
                logger.warning("LLM 리포트 요약 생성 실패", exc_info=True)
                llm_summary = f"지난 {days}일 동안 {total}개의 스크랩과 {diary_count}개의 다이어리를 기록했습니다."

        return ReportResponse(
            period=period,
            date_range=f"{start_date_str} ~ {end_date_str}",
            total_scraps=total,
            total_diaries=diary_count,
            topic_distribution=topic_dist,
            source_distribution=source_dist,
            llm_summary=llm_summary,
            highlights=highlights,
        )

    async def _count_journals(self, user_id: UUID, start: datetime, end: datetime) -> int:
        """기간 내 저널 수 조회."""
        try:
            return await self.calendar_repo.count_diaries_in_range(user_id, start, end)
        except Exception:
            return 0

    async def _generate_llm_summary(
        self,
        period: str,
        titles: list[str],
        tag_counter: Counter,
        total_scraps: int,
        total_diaries: int,
    ) -> tuple[str, list[str]]:
        llm = get_analytical_llm()
        period_kr = "주간" if period == "weekly" else "월간"
        top_tags = ", ".join(t for t, _ in tag_counter.most_common(5))
        title_sample = "\n".join(f"- {t}" for t in titles[:15])

        prompt = f"""당신은 개인 지식 관리 AI 어시스턴트입니다.
사용자의 {period_kr} 활동을 분석하여 한국어로 리포트를 작성하세요.

데이터:
- 기간: {period_kr}
- 저장된 스크랩: {total_scraps}개
- 작성한 다이어리: {total_diaries}개
- 주요 주제: {top_tags}
- 스크랩 제목 예시:
{title_sample}

다음 형식으로 작성하세요:
1. 요약 (2-3문장으로 이 기간의 핵심 활동 요약)
2. 하이라이트 (3-5개 핵심 포인트, 각각 한 줄)

요약과 하이라이트를 === 구분자로 나누어 작성하세요.
===
하이라이트1
하이라이트2
하이라이트3"""

        response = await llm.ainvoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)

        parts = text.split("===")
        summary = parts[0].strip()
        highlights = []
        if len(parts) > 1:
            highlights = [
                h.strip().lstrip("- ").lstrip("0123456789. ") for h in parts[1].strip().split("\n") if h.strip()
            ]

        return summary, highlights[:5]
