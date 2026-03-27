import asyncio
import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from app.config.llm import get_analytical_llm, get_tagger_llm
from app.repositories.diary_repository import DiaryRepository
from app.repositories.diary_scrap_link_repository import DiaryScrapLinkRepository

logger = logging.getLogger(__name__)

# 저널 입력 최소 길이 (이 미만은 의미 있는 분석 불가)
MIN_CONTENT_LENGTH = 10

SENTIMENT_PROMPT = """Classify the overall mood of this journal entry.
Respond with exactly one word: POSITIVE, NEGATIVE, or NEUTRAL.
For mixed-mood entries, choose the dominant emotion.
No explanation."""

TAG_EXTRACTION_PROMPT = """다이어리 내용에서 핵심 키워드 2~3개를 추출하세요.
키워드만 쉼표로 구분해서 반환하세요. (예: 운동, 독서, 프로젝트)
불필요한 설명 없이 키워드만 반환합니다."""


class DiaryService:
    """다이어리 CRUD 및 LLM 기반 감정 분석·태그 추출 비즈니스 로직."""

    def __init__(
        self,
        diary_repo: DiaryRepository,
        link_repo: DiaryScrapLinkRepository | None = None,
    ):
        self.diary_repo = diary_repo
        self.link_repo = link_repo

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _extract_tags_ai_with_retry(self, content: str) -> list[str]:
        """내부 재시도 헬퍼 — 예외 전파. 일시적 API 오류 시 tenacity가 자동 재시도."""
        llm = get_tagger_llm()
        messages = [
            SystemMessage(content=TAG_EXTRACTION_PROMPT),
            HumanMessage(content=content[:1500]),
        ]
        response = await llm.ainvoke(messages)
        tags = [t.strip() for t in response.content.split(",") if t.strip()]
        return tags[:3]

    async def _extract_tags_ai(self, content: str) -> list[str]:
        """AI로 다이어리 핵심 키워드 2~3개 추출. rate-limit 대비 최대 3회 재시도."""
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            return []
        try:
            return await self._extract_tags_ai_with_retry(content)
        except Exception:
            logger.exception("AI 태그 추출 실패")
            return []

    async def _analyze_sentiment(self, content: str) -> str:
        """LLM 기반 감정 분석. POSITIVE / NEGATIVE / NEUTRAL 반환."""
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            return "NEUTRAL"
        try:
            llm = get_analytical_llm()
            messages = [
                SystemMessage(content=SENTIMENT_PROMPT),
                HumanMessage(content=content[:500]),
            ]
            response = await llm.ainvoke(messages)
            result = response.content.strip().upper()
            if result in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                return result
            return "NEUTRAL"
        except Exception:
            logger.exception("LLM 감정 분석 실패, NEUTRAL 반환")
            return "NEUTRAL"

    async def create_entry(
        self,
        user_id: UUID | None,
        content: str,
        scrap_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """다이어리 항목 생성 (감정 분석 + AI 태그 추출 + 스크랩 링크 동기화 포함)."""
        mood, tags = await asyncio.gather(
            self._analyze_sentiment(content),
            self._extract_tags_ai(content),
        )
        diary = await self.diary_repo.create_diary(user_id, content, mood=mood, tags=tags)

        # 스크랩 링크 동기화
        if diary and scrap_ids and self.link_repo:
            try:
                diary_id = UUID(diary["id"])
                await self.link_repo.sync_links(diary_id, scrap_ids, link_type="manual")
            except Exception:
                logger.exception("다이어리-스크랩 링크 동기화 실패 (diary_id=%s)", diary.get("id"))

        return diary

    async def update_entry(
        self,
        diary_id: UUID,
        user_id: UUID,
        content: str,
        scrap_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """다이어리 항목 수정 (감정 재분석 + AI 태그 재추출)."""
        # 소유권 확인
        existing = await self.diary_repo.get_diary_by_id(diary_id, user_id)
        if not existing:
            return None

        mood, tags = await asyncio.gather(
            self._analyze_sentiment(content),
            self._extract_tags_ai(content),
        )
        diary = await self.diary_repo.update_diary(diary_id, content, mood=mood, tags=tags)

        # 스크랩 링크 재동기화
        if diary and scrap_ids is not None and self.link_repo:
            try:
                await self.link_repo.sync_links(diary_id, scrap_ids, link_type="manual")
            except Exception:
                logger.exception("다이어리-스크랩 링크 재동기화 실패 (diary_id=%s)", diary_id)

        return diary

    async def get_entries(self, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        """사용자의 다이어리 항목 목록 조회."""
        return await self.diary_repo.get_diaries(user_id, limit)

    async def get_diary_dates(self, user_id: UUID, limit: int = 90) -> list[dict[str, Any]]:
        """다이어리가 존재하는 날짜 목록 조회."""
        entries = await self.diary_repo.get_diary_dates(user_id, limit)
        date_map: dict[str, dict] = {}
        for e in entries:
            date_str = e["created_at"][:10]
            if date_str not in date_map:
                date_map[date_str] = {
                    "date": date_str,
                    "count": 0,
                    "mood": e.get("mood"),
                    "tags": e.get("tags") or [],
                }
            else:
                # 같은 날 여러 항목: 태그 합산 후 상위 3개 유지
                existing = date_map[date_str]["tags"]
                new_tags = e.get("tags") or []
                merged = list(dict.fromkeys(existing + new_tags))
                date_map[date_str]["tags"] = merged[:3]
            date_map[date_str]["count"] += 1
        return list(date_map.values())

    async def get_diaries_by_date(self, user_id: UUID, date_str: str) -> list[dict[str, Any]]:
        """특정 날짜의 다이어리 목록 조회."""
        return await self.diary_repo.get_diaries_by_date(user_id, date_str)
