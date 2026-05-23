import logging
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config.llm import get_analytical_llm, get_creative_llm
from app.repositories.chat_repository import ChatRepository
from app.repositories.vector_repository import VectorRepository
from app.services.diary_service import MIN_CONTENT_LENGTH
from app.utils import parse_llm_json_response

logger = logging.getLogger(__name__)
MAX_REVIEW_QUESTIONS = 3
MAX_TRANSCRIPT_CHARS = 10000
RELATED_SCRAPS_LIMIT = 5
RELATED_SCRAPS_THRESHOLD = 0.4
RELATED_SCRAP_SUMMARY_LENGTH = 100

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

DRAFT_PROMPT = """You are a reflective journal writing assistant.
Write a first-person journal entry based on the evening conversation transcript.

Structure:
## [Theme-based title in Korean]
[2-3 paragraphs reflecting on key topics, feelings, and insights discussed]

### Key Takeaway
[1-2 sentences: the most important insight or realization]

Rules:
- Write in the same language the user used (Korean if they spoke Korean)
- First person voice ("나는", "오늘은")
- Only reflect what was actually discussed — never add fictional details
- 3-5 paragraphs total, concise but meaningful"""

COGNITIVE_DISTORTION_PROMPT = """You are a cognitive behavioral therapy (CBT) analyst.
Analyze this journal entry for potential cognitive distortions.

**Process:**
1. Separate factual statements from subjective interpretations
2. For each subjective claim, consider evidence for and against
3. Check if any match cognitive distortion patterns

**Distortion Types:**
- all_or_nothing: Absolute thinking in genuinely negative context.
  NOTE: "항상 감사합니다" (always grateful) is NOT a distortion. "항상 실패해" (always fail) IS.
- overgeneralization: One event generalized to universal pattern
- personalization: Taking blame for things outside one's control
- catastrophizing: Assuming worst-case outcome without evidence
- mind_reading: Assuming others' thoughts without verification

**Output JSON:**
{
  "distortions": [
    {
      "type": "overgeneralization",
      "trigger_text": "exact triggering phrase",
      "name": "과잉일반화 (Overgeneralization)",
      "reasoning": "brief analysis in English",
      "feedback": "gentle reframing suggestion in Korean"
    }
  ],
  "wellness_note": "one-sentence assessment in Korean"
}

If no genuine distortions: {"distortions": [], "wellness_note": "건강한 사고 패턴이 관찰됩니다."}

Example:
Input: "오늘 발표를 망쳤다. 나는 항상 중요한 순간에 실수해."
Output:
{
  "distortions": [
    {"type": "overgeneralization", "trigger_text": "항상 중요한 순간에 실수해",
     "name": "과잉일반화 (Overgeneralization)",
     "reasoning": "Generalizes one presentation to all important moments",
     "feedback": "이번 발표에서 구체적으로 어떤 부분이 아쉬웠는지 돌아보면 어떨까요?"}
  ],
  "wellness_note": "한 번의 경험을 일반화하는 경향이 보입니다. 구체적 사실에 집중하면 도움이 될 수 있어요."
}

Return ONLY valid JSON. No markdown."""


class DiaryAnalysisService:
    """다이어리 AI 분석 서비스 — 성찰 질문, 인지 왜곡, 초안 생성, 관련 스크랩 검색."""

    def __init__(
        self,
        chat_repo: ChatRepository | None = None,
        vector_repo: VectorRepository | None = None,
    ):
        self.chat_repo = chat_repo
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

    async def detect_cognitive_distortions(self, content: str) -> dict[str, Any]:
        """저널 내용에서 인지 왜곡 탐지 (LLM 기반 DoT 접근법).

        키워드 매칭 대신 LLM이 사실/주관 분리 → 근거 대조 → 인지 도식 분석 3단계를 수행.
        "항상 감사합니다"와 같은 긍정적 절대어는 왜곡으로 탐지하지 않음.
        """
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            return {"has_distortions": False, "distortions": [], "wellness_score": 85}

        try:
            llm = get_analytical_llm()
            response = await llm.ainvoke(
                [
                    SystemMessage(content=COGNITIVE_DISTORTION_PROMPT),
                    HumanMessage(content=f"Journal entry:\n{content[:2000]}"),
                ]
            )
            result = parse_llm_json_response(response.content.strip())
            distortions = result.get("distortions", [])
            wellness_note = result.get("wellness_note", "")
            wellness_score = max(0, 100 - len(distortions) * 20)
            return {
                "has_distortions": len(distortions) > 0,
                "distortions": distortions,
                "wellness_score": wellness_score,
                "wellness_note": wellness_note,
            }
        except Exception:
            logger.exception("인지 왜곡 LLM 분석 실패, 안전 폴백 반환")
            return {"has_distortions": False, "distortions": [], "wellness_score": 85}

    async def generate_draft_from_conversation(self, session_id: UUID) -> str:
        """저녁 대화 세션으로부터 다이어리 초안 생성 (LLM 활용)."""
        if not self.chat_repo:
            raise ValueError("ChatRepository not available")

        messages = await self.chat_repo.get_messages(session_id)
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

        try:
            llm = get_creative_llm()
            lc_messages = [
                SystemMessage(content=DRAFT_PROMPT),
                HumanMessage(content=f"다음 evening 대화를 바탕으로 다이어리 초안을 작성해주세요:\n\n{transcript}"),
            ]
            response = await llm.ainvoke(lc_messages)
            return response.content
        except Exception:
            logger.exception("다이어리 초안 생성 실패 (session_id=%s)", session_id)
            raise

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
