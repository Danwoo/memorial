import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from app.agents.socrates.state import SocratesState
from app.config.llm import get_analytical_llm

logger = logging.getLogger(__name__)

# 의도 자동 분류 키워드
_COUNTER_KEYWORDS = ["반론", "반대", "비판", "다른 관점", "약점", "문제점", "단점", "criticism"]
_SUMMARY_KEYWORDS = ["요약", "정리", "핵심", "줄여", "summarize"]
_EVENING_KEYWORDS = ["하루 정리", "하루 돌아", "오늘 회고", "저녁 회고", "하루를 마무리"]
_INSIGHT_KEYWORDS = ["깊이 생각", "분석해", "본질", "통찰"]
_ASSUMPTION_KEYWORDS = ["전제", "가정", "전제 분석", "assumption", "숨겨진 가정"]
_FIVE_WHYS_KEYWORDS = ["왜 그런", "근본 원인", "왜?", "5 whys", "파고들"]
_DIALECTIC_KEYWORDS = ["비교", "뭐가 나을", "장단점", "vs", "선택지", "어떤 게 좋"]

QUERY_REWRITE_PROMPT = """You are a search query optimizer for a personal knowledge management system.

Given a conversation history and the user's latest message, rewrite the message into
a standalone search query that captures the user's actual information need.

Rules:
1. Resolve pronouns and references ("that", "it", "the one I mentioned", "그거", "아까")
   using conversation context
2. If the message is already a clear, self-contained query, return it unchanged
3. For comparison requests ("compare X and Y"), output TWO queries separated by |||
4. Keep the query in the same language as the user's message
5. Output ONLY the rewritten query, nothing else

Example 1:
History: User asked about React hooks. AI explained useState.
Latest: "What about the other one?"
Output: React useEffect hook

Example 2:
History: User discussed pros of functional programming
Latest: "그거랑 OOP 비교해줘"
Output: 함수형 프로그래밍 장점 ||| 객체지향 프로그래밍 장점

Example 3:
Latest: "함수형 프로그래밍의 장점은?"
Output: 함수형 프로그래밍의 장점"""


def _detect_intent(message: str) -> str | None:
    """사용자 메시지에서 대화 의도를 키워드 기반으로 자동 분류.

    반환값은 mode 문자열 또는 None(기본).
    """
    msg = message.lower()
    for keywords, mode_value in [
        (_COUNTER_KEYWORDS, "counter"),
        (_SUMMARY_KEYWORDS, "summary"),
        (_EVENING_KEYWORDS, "evening"),
        (_INSIGHT_KEYWORDS, "insight"),
        (_ASSUMPTION_KEYWORDS, "assumption"),
        (_FIVE_WHYS_KEYWORDS, "five_whys"),
        (_DIALECTIC_KEYWORDS, "dialectic"),
    ]:
        if any(kw in msg for kw in keywords):
            return mode_value
    return None


async def _rewrite_query(messages: list, query: str) -> list[str]:
    """대화 맥락 반영 쿼리 재작성. 복합 질의는 분해."""
    if len(messages) <= 1:
        return [query]

    recent = messages[-6:]
    history = "\n".join(f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content[:200]}" for m in recent[:-1])
    try:
        llm = get_analytical_llm()
        response = await llm.ainvoke(
            [
                SystemMessage(content=QUERY_REWRITE_PROMPT),
                HumanMessage(content=f"History:\n{history}\n\nLatest: {query}"),
            ]
        )
        queries = [q.strip() for q in response.content.strip().split("|||") if q.strip()]
        return queries if queries else [query]
    except Exception:
        logger.warning("Query rewrite 실패, 원본 사용")
        return [query]


async def query_understanding_node(state: SocratesState) -> dict:
    """의도 분류 + 쿼리 재작성 노드.

    explicit_mode가 있으면 그대로 사용, 없으면 키워드 기반 자동 분류.
    대화 맥락을 반영하여 검색 쿼리를 재작성하고 복합 질의를 분해한다.
    StreamWriter로 진행 상태를 실시간 전달한다.
    """
    writer = get_stream_writer()
    writer({"node": "query_understanding", "status": "started"})

    user_query = state["user_query"]
    messages = state["messages"]
    explicit_mode = state.get("explicit_mode")

    # explicit_mode 우선, 없으면 자동 분류
    mode = explicit_mode if explicit_mode else _detect_intent(user_query)

    # 쿼리 재작성 (대명사 해소, 복합 쿼리 분해)
    try:
        rewritten_queries = await _rewrite_query(messages, user_query)
    except Exception:
        logger.warning("query_understanding: 쿼리 재작성 실패, 원본 사용")
        rewritten_queries = [user_query]

    search_query = rewritten_queries[0] if rewritten_queries else user_query
    logger.debug("쿼리 재작성: %r → %r", user_query[:50], search_query[:50])

    writer(
        {
            "node": "query_understanding",
            "status": "done",
            "mode": mode,
            "queries": len(rewritten_queries),
        }
    )

    return {
        "detected_mode": mode,
        "rewritten_queries": rewritten_queries,
        "search_query": search_query,
    }
