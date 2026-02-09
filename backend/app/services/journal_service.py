"""
Journal Service
Business logic for journal operations (sentiment, Socratic questions, distortions).
"""
import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config.llm import get_creative_llm
from app.repositories.chat_repository import ChatRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

REVIEWER_PROMPT = """You are a Socratic thinking partner. Based on the user's journal entry, generate 2-3 thoughtful questions that:
1. Help the user think more deeply about their experiences
2. Identify patterns or connections they might have missed
3. Gently challenge any cognitive distortions (black-and-white thinking, overgeneralization, etc.)

Respond in the same language as the journal entry.
Format: Return only the questions, one per line, numbered."""


DRAFT_PROMPT = """You are a reflective journal writing assistant. Based on the evening conversation between the user and their AI thinking partner, write a journal entry draft.

**Guidelines:**
- Write in the same language the user used during the conversation
- Structure the journal as a first-person reflection (use "나는", "오늘은" etc. for Korean)
- Include key topics, feelings, and insights discussed
- Add a brief reflection or takeaway at the end
- Use markdown formatting with headers
- Keep it concise but meaningful (200-400 words)
- Do NOT add fictional details; only reflect what was actually discussed

**Output:** A well-structured journal entry draft in markdown format."""


POSITIVE_SENTIMENT_WORDS = [
    "happy", "good", "great", "excited", "proud", "calm",
    "평온", "행복", "좋아", "성취", "뿌듯",
]

NEGATIVE_SENTIMENT_WORDS = [
    "sad", "bad", "angry", "anxious", "tired",
    "우울", "슬퍼", "힘들", "피곤", "짜증", "불안",
]

COGNITIVE_DISTORTION_PATTERNS = {
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


class JournalService:
    def __init__(
        self,
        journal_repo: JournalRepository,
        graph_repo: GraphRepository,
        vector_repo: VectorRepository | None = None,
        chat_repo: ChatRepository | None = None,
    ):
        self.journal_repo = journal_repo
        self.graph_repo = graph_repo
        self.vector_repo = vector_repo
        self.chat_repo = chat_repo

    def _analyze_sentiment(self, content: str) -> str:
        """
        Simple keyword-based sentiment analysis for MVP.
        TODO: Replace with LLM or VADER.
        """
        score = 0
        content_lower = content.lower()

        for word in POSITIVE_SENTIMENT_WORDS:
            if word in content_lower:
                score += 1
        for word in NEGATIVE_SENTIMENT_WORDS:
            if word in content_lower:
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

        for pattern_id, pattern in COGNITIVE_DISTORTION_PATTERNS.items():
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

    async def generate_draft_from_conversation(self, session_id: UUID) -> str:
        """
        Generate a journal draft from an evening chat session.
        Reads the conversation history and asks LLM to write a reflective journal.
        """
        if not self.chat_repo:
            raise ValueError("ChatRepository not available")

        messages = await self.chat_repo.get_messages(session_id)
        if not messages:
            raise ValueError("No messages found in session")

        # Build conversation transcript
        transcript_lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                transcript_lines.append(f"사용자: {msg.content}")
            elif isinstance(msg, AIMessage):
                transcript_lines.append(f"AI: {msg.content}")

        transcript = "\n\n".join(transcript_lines)

        # Truncate if too long
        if len(transcript) > 10000:
            transcript = transcript[:10000] + "\n\n[대화 내용 일부 생략...]"

        llm = get_creative_llm()
        lc_messages = [
            SystemMessage(content=DRAFT_PROMPT),
            HumanMessage(content=f"다음 evening 대화를 바탕으로 저널 초안을 작성해주세요:\n\n{transcript}"),
        ]

        response = await llm.ainvoke(lc_messages)
        return response.content

    async def get_related_memories(
        self, user_id: UUID, content: str
    ) -> list[dict[str, Any]]:
        """Find memories related to journal content via vector similarity search."""
        if not self.vector_repo:
            return []

        if not content or len(content.strip()) < 10:
            return []

        try:
            results = await self.vector_repo.similarity_search(
                query=content,
                limit=5,
                threshold=0.4,
                filters={"user_id": str(user_id)},
            )
            return [
                {
                    "id": m.get("id"),
                    "title": m.get("title", "Untitled"),
                    "summary": m.get("summary") or m.get("content", "")[:100],
                    "type": m.get("type", "memory"),
                    "created_at": m.get("created_at"),
                    "similarity": m.get("similarity", 0),
                }
                for m in results
            ]
        except Exception:
            logger.exception("Failed to fetch related memories")
            return []
