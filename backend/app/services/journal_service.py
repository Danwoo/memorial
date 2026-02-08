"""
Journal Service
Business logic for journal operations (sentiment, Socratic questions, distortions).
"""
import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.llm import get_creative_llm
from app.repositories.graph_repository import GraphRepository
from app.repositories.journal_repository import JournalRepository

logger = logging.getLogger(__name__)

REVIEWER_PROMPT = """You are a Socratic thinking partner. Based on the user's journal entry, generate 2-3 thoughtful questions that:
1. Help the user think more deeply about their experiences
2. Identify patterns or connections they might have missed
3. Gently challenge any cognitive distortions (black-and-white thinking, overgeneralization, etc.)

Respond in the same language as the journal entry.
Format: Return only the questions, one per line, numbered."""


class JournalService:
    def __init__(self, journal_repo: JournalRepository, graph_repo: GraphRepository):
        self.journal_repo = journal_repo
        self.graph_repo = graph_repo

    def _analyze_sentiment(self, content: str) -> str:
        """
        Simple keyword-based sentiment analysis for MVP.
        TODO: Replace with LLM or VADER.
        """
        pos_words = ["happy", "good", "great", "excited", "proud", "calm", "평온", "행복", "좋아", "성취", "뿌듯"]
        neg_words = ["sad", "bad", "angry", "anxious", "tired", "우울", "슬퍼", "힘들", "피곤", "짜증", "불안"]

        score = 0
        content_lower = content.lower()

        for w in pos_words:
            if w in content_lower:
                score += 1
        for w in neg_words:
            if w in content_lower:
                score -= 1

        if score > 0:
            return "POSITIVE"
        if score < 0:
            return "NEGATIVE"
        return "NEUTRAL"

    async def create_entry(self, user_id: UUID | None, content: str) -> dict[str, Any] | None:
        """Create a journal entry with mood analysis."""
        mood = self._analyze_sentiment(content)
        journal = await self.journal_repo.create_journal(user_id, content, mood=mood)
        return journal

    async def get_entries(self, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        """Get journal entries for a user."""
        return await self.journal_repo.get_journals(user_id, limit)

    def generate_review_questions(self, content: str) -> list[str]:
        """
        Generate Socratic review questions based on journal content.
        Uses LLM to create thoughtful, reflective questions.
        """
        if not content or len(content.strip()) < 10:
            return ["오늘 하루 중 가장 기억에 남는 순간은 무엇인가요?"]

        try:
            llm = get_creative_llm()

            messages = [
                SystemMessage(content=REVIEWER_PROMPT),
                HumanMessage(content=f"Journal Entry:\n{content}"),
            ]

            response = llm.invoke(messages)

            questions = [q.strip() for q in response.content.split("\n") if q.strip()]
            return questions[:3]

        except Exception:
            logger.exception("Error generating review questions")
            return ["이 경험에서 어떤 인사이트를 얻었나요?"]

    def detect_cognitive_distortions(self, content: str) -> dict[str, Any]:
        """
        Detect cognitive distortions in journal content.
        Returns detected patterns and gentle reframing suggestions.
        """
        content_lower = content.lower()
        detected = []

        patterns = {
            "all_or_nothing": {
                "name": "흑백논리 (All-or-Nothing)",
                "keywords": ["항상", "절대", "전혀", "never", "always", "완전히", "100%"],
                "feedback": "상황에 중간 지대가 있을 수 있어요. '때때로' 또는 '어떤 경우에는'으로 표현해보면 어떨까요?",
            },
            "overgeneralization": {
                "name": "과잉일반화 (Overgeneralization)",
                "keywords": ["매번", "언제나", "늘", "이런 식이야", "맨날", "every time"],
                "feedback": "구체적인 이번 상황에 집중해보면 어떨까요? 실제로 매번 그랬나요?",
            },
            "personalization": {
                "name": "개인화 (Personalization)",
                "keywords": ["내 탓", "내가 잘못", "내 책임", "나 때문에", "my fault"],
                "feedback": "상황에 영향을 준 다른 요인들도 있지 않았을까요?",
            },
            "catastrophizing": {
                "name": "파국화 (Catastrophizing)",
                "keywords": ["끔찍", "최악", "재앙", "망했", "terrible", "disaster", "worst"],
                "feedback": "현실적으로 가장 가능성 높은 결과는 무엇일까요?",
            },
            "mind_reading": {
                "name": "독심술 (Mind Reading)",
                "keywords": ["~라고 생각할 거야", "분명히 ~일 거야", "나를 싫어", "무시하", "think I'm"],
                "feedback": "실제로 상대방에게 확인해보셨나요? 다른 해석도 가능할 수 있어요.",
            },
        }

        for pattern_id, pattern in patterns.items():
            for keyword in pattern["keywords"]:
                if keyword in content_lower:
                    detected.append({
                        "type": pattern_id,
                        "name": pattern["name"],
                        "trigger": keyword,
                        "feedback": pattern["feedback"],
                    })
                    break  # One match per pattern is enough

        return {
            "has_distortions": len(detected) > 0,
            "distortions": detected,
            "wellness_score": max(0, 100 - len(detected) * 20),
        }
