import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config.llm import get_creative_llm
from app.repositories.socrates_repository import SocratesRepository
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 10
MAX_REVIEW_QUESTIONS = 3
MAX_TRANSCRIPT_CHARS = 10000
RELATED_SCRAPS_LIMIT = 5
RELATED_SCRAPS_THRESHOLD = 0.4
RELATED_SCRAP_SUMMARY_LENGTH = 100
WELLNESS_PENALTY_PER_DISTORTION = 20

REVIEWER_PROMPT = """당신은 소크라테스식 사고 파트너입니다. 사용자의 저널 내용을 읽고, 2-3개의 깊이 있는 성찰 질문을 생성하세요.

**질문 생성 원칙:**
1. 사용자가 경험을 더 깊이 성찰하도록 돕는 질문
2. 놓쳤을 수 있는 패턴이나 연결고리를 발견하게 하는 질문
3. 인지 왜곡(흑백논리, 과잉일반화 등)을 부드럽게 도전하는 질문

**저널 유형별 차별화:**
- TIL/학습 저널: "이 개념을 실제 프로젝트에 적용한다면?" "이전에 배운 것과 어떤 연결이 있나요?"
- 프로젝트 회고: "이 경험에서 팀/개인으로서 성장한 점은?" "다음에 같은 상황이 오면 무엇을 다르게 하겠습니까?"
- 감정/일상 회고: "이 감정의 근본 원인은 무엇일까요?" "비슷한 상황에서 다른 해석도 가능할까요?"
- 주간 회고: "이번 주의 핵심 테마는 무엇인가요?" "에너지를 가장 많이 준/뺏은 것은?"

**반드시 한국어로 질문을 생성하세요.**
형식: 질문만 반환, 줄바꿈으로 구분, 번호 매기기."""

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


class DiaryAnalysisService:
    """다이어리 AI 분석 서비스 — 성찰 질문, 인지 왜곡, 초안 생성, 관련 스크랩 검색."""

    def __init__(
        self,
        socrates_repo: SocratesRepository | None = None,
        vector_repo: VectorRepository | None = None,
    ):
        self.socrates_repo = socrates_repo
        self.vector_repo = vector_repo

    async def generate_review_questions(self, content: str) -> list[str]:
        """저널 내용 기반 소크라테스식 성찰 질문 생성 (LLM 활용)."""
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            return ["오늘 하루 중 가장 기억에 남는 순간은 무엇인가요?"]

        try:
            llm = get_creative_llm()
            messages = [
                SystemMessage(content=REVIEWER_PROMPT),
                HumanMessage(content=f"Journal Entry:\n{content}"),
            ]
            response = await llm.ainvoke(messages)
            questions = [q.strip() for q in response.content.split("\n") if q.strip()]
            return questions[:MAX_REVIEW_QUESTIONS]
        except Exception:
            logger.exception("성찰 질문 생성 실패")
            return ["이 경험에서 어떤 인사이트를 얻었나요?"]

    def detect_cognitive_distortions(self, content: str) -> dict[str, Any]:
        """저널 내용에서 인지 왜곡 탐지. 탐지된 패턴과 리프레이밍 제안 반환."""
        content_lower = content.lower()
        detected = []

        for pattern_id, pattern in COGNITIVE_DISTORTION_PATTERNS.items():
            for keyword in pattern["keywords"]:
                if keyword in content_lower:
                    detected.append(
                        {
                            "type": pattern_id,
                            "name": pattern["name"],
                            "trigger": keyword,
                            "feedback": pattern["feedback"],
                        }
                    )
                    break

        return {
            "has_distortions": len(detected) > 0,
            "distortions": detected,
            "wellness_score": max(0, 100 - len(detected) * WELLNESS_PENALTY_PER_DISTORTION),
        }

    async def generate_draft_from_conversation(self, session_id: UUID) -> str:
        """저녁 대화 세션으로부터 다이어리 초안 생성 (LLM 활용)."""
        if not self.socrates_repo:
            raise ValueError("SocratesRepository not available")

        messages = await self.socrates_repo.get_messages(session_id)
        if not messages:
            raise ValueError("No messages found in session")

        transcript_lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                transcript_lines.append(f"사용자: {msg.content}")
            elif isinstance(msg, AIMessage):
                transcript_lines.append(f"AI: {msg.content}")

        transcript = "\n\n".join(transcript_lines)
        if len(transcript) > MAX_TRANSCRIPT_CHARS:
            transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[대화 내용 일부 생략...]"

        llm = get_creative_llm()
        lc_messages = [
            SystemMessage(content=DRAFT_PROMPT),
            HumanMessage(content=f"다음 evening 대화를 바탕으로 다이어리 초안을 작성해주세요:\n\n{transcript}"),
        ]
        response = await llm.ainvoke(lc_messages)
        return response.content

    async def get_related_scraps(self, user_id: UUID, content: str) -> list[dict[str, Any]]:
        """다이어리 내용과 유사한 Scrap을 벡터 검색으로 조회."""
        if not self.vector_repo:
            return []
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            return []

        try:
            results = await self.vector_repo.similarity_search(
                query=content,
                limit=RELATED_SCRAPS_LIMIT,
                threshold=RELATED_SCRAPS_THRESHOLD,
                filters={"user_id": str(user_id)},
            )
            return [
                {
                    "id": m.get("id"),
                    "title": m.get("title", "Untitled"),
                    "summary": m.get("summary") or m.get("content", "")[:RELATED_SCRAP_SUMMARY_LENGTH],
                    "type": m.get("type", "scrap"),
                    "created_at": m.get("created_at"),
                    "similarity": m.get("similarity", 0),
                }
                for m in results
            ]
        except Exception:
            logger.exception("관련 스크랩 조회 실패")
            return []
