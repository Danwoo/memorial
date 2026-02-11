import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.llm import get_creative_llm
from app.repositories.chat_repository import ChatRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.memory_repository import MemoryRepository
from app.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

MAX_MEMORIES_IN_DIGEST = 10
MAX_JOURNALS_IN_DIGEST = 5

DIGEST_QUESTION_PROMPT = """Based on the user's collected memories from today, generate 1-2 thoughtful questions
to help them reflect on their day. Focus on:
1. Connections between different pieces of content
2. Potential insights or learnings
3. How this relates to their ongoing projects or interests

Respond in Korean. Return only the questions, one per line."""


class DigestService:
    """일일 다이제스트 집계 및 AI 인사이트 생성 서비스."""

    def __init__(
        self,
        memory_repo: MemoryRepository,
        journal_repo: JournalRepository,
        chat_repo: ChatRepository | None = None,
    ):
        self.memory_repo = memory_repo
        self.journal_repo = journal_repo
        self.chat_repo = chat_repo

    @staticmethod
    def _parse_iso_datetime(iso_str: str) -> datetime:
        return parse_iso_datetime(iso_str)

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

        memories = await self._get_today_memories(today_start, today_end, user_id=user_id)
        journals = await self._get_today_journals(user_id, today)
        chats = []  # TODO: 채팅 이력 구현 시 연동

        main_topics = self._extract_topics(memories)
        suggested_questions = await self._generate_questions(memories, journals)

        return {
            "date": today.isoformat(),
            "summary": {"memory_count": len(memories), "journal_count": len(journals), "chat_count": len(chats)},
            "memories": [
                {
                    "id": str(memory.get("id", "")),
                    "title": memory.get("title", "Untitled"),
                    "type": memory.get("source_type", "UNKNOWN"),
                    "summary": memory.get("summary") or memory.get("content", "")[:150],
                    "tags": memory.get("tags") or [],
                    "created_at": memory.get("created_at", ""),
                }
                for memory in memories[:MAX_MEMORIES_IN_DIGEST]
            ],
            "journals": [
                {
                    "id": str(journal.get("id", "")),
                    "mood": journal.get("mood", "NEUTRAL"),
                    "preview": journal.get("content", "")[:100],
                    "created_at": journal.get("created_at", ""),
                }
                for journal in journals[:MAX_JOURNALS_IN_DIGEST]
            ],
            "chats": chats,
            "insights": {"main_topics": main_topics[:5], "suggested_questions": suggested_questions},
        }

    async def _get_today_memories(self, start: datetime, end: datetime, user_id: UUID | None = None) -> list[dict]:
        """오늘 생성된 Memory 조회."""
        try:
            all_memories = await self.memory_repo.get_all(user_id=user_id)

            today_memories = []
            for memory in all_memories:
                created_at_str = memory.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = self._parse_iso_datetime(created_at_str)
                        if start <= created_at <= end:
                            today_memories.append(memory)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping memory with unparseable date: %s", e)

            return today_memories
        except Exception:
            logger.exception("Error fetching today's memories")
            return []

    async def _get_today_journals(self, user_id: UUID, today: datetime) -> list[dict]:
        """오늘 생성된 저널 조회."""
        try:
            journals = await self.journal_repo.get_journals(
                user_id,
                limit=20,
            )

            today_journals = []
            for journal in journals:
                created_at_str = journal.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = self._parse_iso_datetime(created_at_str)
                        if created_at.date() == today:
                            today_journals.append(journal)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping journal with unparseable date: %s", e)

            return today_journals
        except Exception:
            logger.exception("Error fetching today's journals")
            return []

    def _extract_topics(self, memories: list[dict]) -> list[str]:
        """Memory 태그에서 주요 토픽 추출."""
        tag_counts = {}
        for memory in memories:
            for tag in memory.get("tags", []) or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags]

    async def _generate_questions(self, memories: list[dict], journals: list[dict]) -> list[str]:
        """오늘 콘텐츠 기반 AI 성찰 질문 생성."""
        if not memories and not journals:
            return ["오늘 하루는 어떠셨나요?"]

        context_parts = []

        for memory in memories[:5]:
            title = memory.get("title", "Untitled")
            summary = memory.get("summary") or memory.get("content", "")[:100]
            context_parts.append(f"- {title}: {summary}")

        for journal in journals[:2]:
            mood = journal.get("mood", "NEUTRAL")
            preview = journal.get("content", "")[:100]
            context_parts.append(f"- [Journal, Mood: {mood}] {preview}")

        if not context_parts:
            return ["오늘 저장한 내용들을 돌아보면서 어떤 생각이 드시나요?"]

        try:
            llm = get_creative_llm()

            messages = [
                SystemMessage(content=DIGEST_QUESTION_PROMPT),
                HumanMessage(content="Today's content:\n" + "\n".join(context_parts)),
            ]

            response = await llm.ainvoke(messages)
            questions = [q.strip() for q in response.content.split("\n") if q.strip()]
            return questions[:2]

        except Exception:
            logger.exception("Error generating questions")
            return ["오늘 저장한 내용들에서 어떤 인사이트를 얻으셨나요?"]
