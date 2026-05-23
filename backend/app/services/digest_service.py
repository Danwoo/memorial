import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.llm import get_creative_llm
from app.repositories.chat_repository import ChatRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.scrap_repository import ScrapRepository
from app.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

MAX_SCRAPS_IN_DIGEST = 10
MAX_DIARIES_IN_DIGEST = 5
MAX_DIGEST_TOPICS = 5
# 다이제스트 미리보기 길이
SCRAP_SUMMARY_PREVIEW_LENGTH = 150
DIARY_PREVIEW_LENGTH = 100
QUESTION_CONTEXT_PREVIEW_LENGTH = 100
# 질문 생성에 참조할 최대 항목 수
MAX_SCRAP_CONTEXT_ITEMS = 5
MAX_DIARY_CONTEXT_ITEMS = 2
MAX_GENERATED_QUESTIONS = 2
# 저널 조회 제한
MAX_JOURNAL_FETCH_LIMIT = 20

DIGEST_QUESTION_PROMPT = """You are a reflective thinking partner.
Given the user's saved content from today, generate 1-2 questions that help them
discover connections or insights they might have missed.

Rules:
1. Reference specific content titles/topics from the input
2. Ask "why" or "how" questions that require reflection
3. If multiple pieces of content exist, ask about connections between them
4. Output in Korean, one question per line, no numbering

Example:
Content: "React Server Components article", "Team retrospective diary (mood: positive)"
Output:
오늘 읽은 React Server Components 글이 현재 팀 프로젝트에 적용할 수 있는 부분이 있을까요?
팀 회고에서 느낀 긍정적 에너지의 원천은 무엇이었나요?"""


class DigestService:
    """일일 다이제스트 집계 및 AI 인사이트 생성 서비스."""

    def __init__(
        self,
        scrap_repo: ScrapRepository,
        diary_repo: DiaryRepository,
        chat_repo: ChatRepository | None = None,
    ):
        self.scrap_repo = scrap_repo
        self.diary_repo = diary_repo
        self.chat_repo = chat_repo

    async def get_today_digest(self, user_id: UUID, target_date: datetime | None = None) -> dict[str, Any]:
        """하루 활동 종합 다이제스트 조회.

        Args:
            user_id: 대상 사용자 ID
            target_date: 조회 대상 날짜 (기본값: 오늘)

        Returns:
            memories, journals, chats, insights 포함 다이제스트 dict
        """
        today = target_date or datetime.now(UTC).date()
        if isinstance(today, datetime):
            today = today.date()
        today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
        today_end = datetime.combine(today, datetime.max.time(), tzinfo=UTC)

        scraps = await self._get_today_scraps(today_start, today_end, user_id=user_id)
        diaries = await self._get_today_diaries(user_id, today)
        chats = await self._get_today_chats(today_start, today_end, user_id=user_id)

        main_topics = self._extract_topics(scraps)
        suggested_questions = await self._generate_questions(scraps, diaries)

        return {
            "date": today.isoformat(),
            "summary": {"scrap_count": len(scraps), "diary_count": len(diaries), "chat_count": len(chats)},
            "scraps": [
                {
                    "id": str(scrap.get("id", "")),
                    "title": scrap.get("title", "Untitled"),
                    "type": scrap.get("source_type", "UNKNOWN"),
                    "summary": scrap.get("summary") or scrap.get("content", "")[:SCRAP_SUMMARY_PREVIEW_LENGTH],
                    "tags": scrap.get("tags") or [],
                    "created_at": scrap.get("created_at", ""),
                }
                for scrap in scraps[:MAX_SCRAPS_IN_DIGEST]
            ],
            "diaries": [
                {
                    "id": str(diary.get("id", "")),
                    "mood": diary.get("mood", "NEUTRAL"),
                    "preview": diary.get("content", "")[:DIARY_PREVIEW_LENGTH],
                    "created_at": diary.get("created_at", ""),
                }
                for diary in diaries[:MAX_DIARIES_IN_DIGEST]
            ],
            "chats": chats,
            "insights": {"main_topics": main_topics[:MAX_DIGEST_TOPICS], "suggested_questions": suggested_questions},
        }

    async def _get_today_scraps(self, start: datetime, end: datetime, user_id: UUID | None = None) -> list[dict]:
        """오늘 생성된 Scrap 조회 (DB 날짜 범위 쿼리)."""
        if not user_id:
            return []
        try:
            return await self.scrap_repo.get_by_date_range(
                user_id=user_id,
                start=start.isoformat(),
                end=end.isoformat(),
            )
        except Exception:
            logger.exception("Error fetching today's scraps")
            return []

    async def _get_today_chats(self, start: datetime, end: datetime, user_id: UUID) -> list[dict]:
        """오늘 생성된 채팅 세션 조회."""
        if not self.chat_repo:
            return []
        try:
            return await self.chat_repo.get_sessions_by_date_range(
                user_id=user_id,
                start_iso=start.isoformat(),
                end_iso=end.isoformat(),
            )
        except Exception:
            logger.exception("오늘 채팅 세션 조회 실패")
            return []

    async def _get_today_diaries(self, user_id: UUID, today: datetime) -> list[dict]:
        """오늘 생성된 다이어리 조회."""
        try:
            journals = await self.diary_repo.get_diaries(
                user_id,
                limit=MAX_JOURNAL_FETCH_LIMIT,
            )

            today_journals = []
            for journal in journals:
                created_at_str = journal.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = parse_iso_datetime(created_at_str)
                        if created_at.date() == today:
                            today_journals.append(journal)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping journal with unparseable date: %s", e)

            return today_journals
        except Exception:
            logger.exception("Error fetching today's diaries")
            return []

    def _extract_topics(self, scraps: list[dict]) -> list[str]:
        """Scrap 태그에서 주요 토픽 추출."""
        tag_counts = {}
        for scrap in scraps:
            for tag in scrap.get("tags", []) or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags]

    async def _generate_questions(self, scraps: list[dict], diaries: list[dict]) -> list[str]:
        """오늘 콘텐츠 기반 AI 성찰 질문 생성."""
        if not scraps and not diaries:
            return ["오늘 하루는 어떠셨나요?"]

        context_parts = []

        for scrap in scraps[:MAX_SCRAP_CONTEXT_ITEMS]:
            title = scrap.get("title", "Untitled")
            summary = scrap.get("summary") or scrap.get("content", "")[:QUESTION_CONTEXT_PREVIEW_LENGTH]
            context_parts.append(f"- {title}: {summary}")

        for diary in diaries[:MAX_DIARY_CONTEXT_ITEMS]:
            mood = diary.get("mood", "NEUTRAL")
            preview = diary.get("content", "")[:QUESTION_CONTEXT_PREVIEW_LENGTH]
            context_parts.append(f"- [Diary, Mood: {mood}] {preview}")

        if not context_parts:
            return ["오늘 저장한 내용들을 돌아보면서 어떤 생각이 드시나요?"]

        try:
            llm = get_creative_llm()

            messages = [
                SystemMessage(content=DIGEST_QUESTION_PROMPT),
                HumanMessage(content="Today's content:\n" + "\n".join(context_parts)),
            ]

            response = await asyncio.wait_for(llm.ainvoke(messages), timeout=5.0)
            questions = [q.strip() for q in response.content.split("\n") if q.strip()]
            return questions[:MAX_GENERATED_QUESTIONS]

        except TimeoutError:
            logger.warning("LLM timeout while generating digest questions")
            return ["오늘 저장한 내용들에서 어떤 인사이트를 얻으셨나요?"]
        except Exception:
            logger.exception("Error generating questions")
            return ["오늘 저장한 내용들에서 어떤 인사이트를 얻으셨나요?"]
