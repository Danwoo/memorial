import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from app.agents.socrates.state import SocratesState
from app.config.llm import get_analytical_llm
from app.utils import parse_llm_json_response

logger = logging.getLogger(__name__)

# 유효한 mode / retrieval_plan 값 집합
_VALID_MODES = {
    "insight",
    "counter",
    "summary",
    "evening",
    "assumption",
    "five_whys",
    "dialectic",
    "connection",
    "compare",
    "deep_dive",
}
_VALID_PLANS = {"no_retrieval", "deep_diary", "simple_search", "full_rag"}

# deep_diary는 초반 턴(≤2)에만 유효 — 이후 full_rag로 강등
_DEEP_DIARY_MAX_TURN = 2

UNIFIED_QUERY_ANALYSIS_PROMPT = """You are a query analyzer for a personal knowledge management system with diary, scrap, and chat features.

Given the user's message and conversation context, output a JSON object with three fields:

1. "mode": The conversation intent. Choose ONE or null:
   - "insight": Deep analysis, exploring assumptions, seeking understanding
   - "counter": Requesting counterarguments, criticism, opposing viewpoints
   - "summary": Asking for summary or synthesis
   - "evening": End-of-day reflection, reviewing the day
   - "assumption": Analyzing hidden premises
   - "five_whys": Drilling into root causes
   - "dialectic": Comparing options, weighing pros and cons
   - "connection": Discovering links between saved scraps
   - "compare": Systematic comparison of saved content
   - "deep_dive": In-depth exploration of a specific topic
   - null: General conversation, greeting, simple question

2. "retrieval_plan": Search strategy. Choose ONE:
   - "no_retrieval": Greetings, thanks, simple acks, small talk
   - "deep_diary": Emotional expression, mood, journaling, personal struggles
   - "simple_search": Simple factual lookup
   - "full_rag": Complex questions needing multi-source analysis

3. "search_queries": Array of 1-2 rewritten search queries.
   - Resolve pronouns using conversation history
   - For comparisons, split into two queries
   - For no_retrieval, return original message as-is

Examples:
User: "안녕" -> {"mode": null, "retrieval_plan": "no_retrieval", "search_queries": ["안녕"]}
User: "오늘 발표 망해서 너무 창피해" -> {"mode": null, "retrieval_plan": "deep_diary", "search_queries": ["발표 실패 후 창피함"]}
User: "이 주장에 반론 있어?" -> {"mode": "counter", "retrieval_plan": "full_rag", "search_queries": ["주장에 대한 반론"]}
User: "함수형 vs OOP 비교" -> {"mode": "dialectic", "retrieval_plan": "full_rag", "search_queries": ["함수형 프로그래밍 장점", "OOP 장점"]}
User: "응" -> {"mode": null, "retrieval_plan": "no_retrieval", "search_queries": ["응"]}

Return ONLY valid JSON."""


async def _unified_query_analysis(messages: list, query: str) -> dict:
    """단일 LLM 호출로 mode + retrieval_plan + search_queries 통합 분석."""
    recent = messages[-6:]
    history_lines = []
    for m in recent[:-1]:
        role = "User" if isinstance(m, HumanMessage) else "AI"
        history_lines.append(f"{role}: {m.content[:200]}")
    history = "\n".join(history_lines)

    user_content = f"History:\n{history}\n\nLatest message: {query}" if history else f"Latest message: {query}"

    llm = get_analytical_llm()
    llm_with_json = llm.bind(response_format={"type": "json_object"})
    response = await llm_with_json.ainvoke(
        [
            SystemMessage(content=UNIFIED_QUERY_ANALYSIS_PROMPT),
            HumanMessage(content=user_content),
        ]
    )
    return parse_llm_json_response(response.content.strip())


async def query_understanding_node(state: SocratesState) -> dict:
    """LLM 기반 통합 쿼리 분석 노드.

    단일 LLM 호출로 대화 의도(mode), 검색 전략(retrieval_plan), 재작성 쿼리를 한번에 결정한다.
    explicit_mode가 있으면 mode를 오버라이드한다.
    deep_diary는 초반 턴(≤2)에만 유효하며, 이후 full_rag로 강등된다.
    LLM 실패 시 안전 폴백(full_rag)을 사용한다.
    """
    writer = get_stream_writer()
    writer({"node": "query_understanding", "status": "started"})

    user_query = state["user_query"]
    messages = state["messages"]
    explicit_mode = state.get("explicit_mode")
    turn_count = state.get("turn_count", 0)

    # LLM 통합 분석
    try:
        result = await _unified_query_analysis(messages, user_query)

        # 필드 유효성 검증
        raw_mode = result.get("mode")
        mode = raw_mode if raw_mode in _VALID_MODES else None

        raw_plan = result.get("retrieval_plan", "full_rag")
        plan = raw_plan if raw_plan in _VALID_PLANS else "full_rag"

        queries_raw = result.get("search_queries", [user_query])
        rewritten_queries = [q.strip() for q in queries_raw if isinstance(q, str) and q.strip()]
        if not rewritten_queries:
            rewritten_queries = [user_query]

    except Exception:
        logger.warning("query_understanding: LLM 분석 실패, 안전 폴백 사용")
        mode = None
        plan = "full_rag"
        rewritten_queries = [user_query]

    # explicit_mode 오버라이드 (UI에서 모드 선택 시)
    if explicit_mode and explicit_mode in _VALID_MODES:
        mode = explicit_mode

    # deep_diary 턴 게이팅: 턴이 깊어지면 full_rag로 강등
    if plan == "deep_diary" and turn_count > _DEEP_DIARY_MAX_TURN:
        logger.debug(
            "query_understanding: turn_count=%d > %d, deep_diary → full_rag 강등", turn_count, _DEEP_DIARY_MAX_TURN
        )
        plan = "full_rag"

    search_query = rewritten_queries[0]
    logger.debug("query_understanding: mode=%s, plan=%s, queries=%r", mode, plan, rewritten_queries)

    writer(
        {
            "node": "query_understanding",
            "status": "done",
            "mode": mode,
            "plan": plan,
            "queries": len(rewritten_queries),
        }
    )

    return {
        "detected_mode": mode,
        "retrieval_plan": plan,
        "rewritten_queries": rewritten_queries,
        "search_query": search_query,
    }
