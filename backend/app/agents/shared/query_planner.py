import logging
import re

from langgraph.config import get_stream_writer

from app.agents.base_state import ChatPipelineState

logger = logging.getLogger(__name__)

# 인사/감사 등 no_retrieval 패턴
_NO_RETRIEVAL_PATTERNS = [
    r"^(안녕|hello|hi|hey|반가워|좋은\s*아침|좋은\s*저녁|잘\s*있어|잘\s*지내)",
    r"^(감사|고마워|땡큐|thank|수고|화이팅)",
    r"^(응|네|아|오|맞아|그렇구나|알겠어|알았어|확인|ok|okay)[\s!.]*$",
    r"^(ㅇㅇ|ㅋ+|ㅎ+|ㄴㄴ)[\s]*$",
]
_NO_RETRIEVAL_RE = [re.compile(p, re.IGNORECASE) for p in _NO_RETRIEVAL_PATTERNS]

# 감정/다이어리 → deep_diary 패턴 (Socrates 전용으로 의미 있음)
_DEEP_DIARY_KEYWORDS = [
    "일기",
    "다이어리",
    "오늘 하루",
    "오늘 기분",
    "힘들었",
    "슬펐",
    "기뻤",
    "화났",
    "속상",
    "우울",
    "불안",
    "걱정",
    "감정",
    "마음이",
]


def _is_no_retrieval(query: str) -> bool:
    """쿼리가 인사/감사/단순 확인 등 검색 불필요 케이스인지 판단."""
    q = query.strip()
    if len(q) <= 10:
        for pattern in _NO_RETRIEVAL_RE:
            if pattern.search(q):
                return True
    return False


def _is_deep_diary(query: str, mode: str | None) -> bool:
    """감정/일기 관련 깊은 대화가 필요한지 판단 (Socrates 에이전트 전용)."""
    if mode in ("evening", "reflection"):
        return True
    q = query.lower()
    return any(kw in q for kw in _DEEP_DIARY_KEYWORDS)


async def query_planner_node(state: ChatPipelineState) -> dict:
    """검색 전략 분류 노드.

    쿼리 복잡도에 따라 검색 전략을 결정한다:
    - no_retrieval: 인사, 감사, 단순 확인 — 벡터 검색 없이 즉시 응답
    - simple_search: 단순 키워드 검색으로 충분한 질문 — memory_retrieval만
    - full_rag: 복잡한 질문 — memory + context + graph 전체 실행
    - deep_diary: 감정/일기 관련 깊은 대화 — diary 검색 포함 (Socrates 전용)

    키워드 기반 빠른 분류 우선. 불분명한 경우 full_rag 폴백.
    """
    writer = get_stream_writer()
    writer({"node": "query_planner", "status": "started"})

    user_query = state.get("user_query", "")
    detected_mode = state.get("detected_mode")
    turn_count = state.get("turn_count", 0)

    # 1. 인사/감사 → no_retrieval (LLM 호출 없이 즉시 결정)
    if _is_no_retrieval(user_query):
        plan = "no_retrieval"
    # 2. 첫 턴 + 감정 키워드 → deep_diary
    elif turn_count <= 2 and _is_deep_diary(user_query, detected_mode):
        plan = "deep_diary"
    # 3. 짧고 단순한 질문 → simple_search
    elif len(user_query.strip()) < 30 and detected_mode not in ("counter", "dialectic", "compare"):
        plan = "simple_search"
    # 4. 그 외 → full_rag
    else:
        plan = "full_rag"

    logger.debug("query_planner: query=%s, plan=%s", user_query[:50], plan)
    writer({"node": "query_planner", "status": "done", "plan": plan})

    return {"retrieval_plan": plan}
