import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

CONTEXT_BUDGET_CHARS = 4000
CONNECTION_SUGGEST_LOW = 0.80
CONNECTION_SUGGEST_HIGH = 0.92
CONNECTION_TURN_INTERVAL = 3
PREVIOUS_SESSION_LIMIT = 3

# Oracle 에이전트 전환 제안 키워드
_DIARY_KEYWORDS = ["일기", "다이어리", "감정", "오늘 하루", "기분", "느낌", "마음", "힘들", "슬프", "기쁘"]
_SCRAP_KEYWORDS = ["스크랩", "저장한", "아티클", "링크", "기사", "요약", "정리", "연결", "관계"]


def _detect_agent_switch_suggestion(message: str) -> str | None:
    """사용자 메시지에서 에이전트 전환 힌트를 감지."""
    msg = message.lower()
    if any(kw in msg for kw in _DIARY_KEYWORDS):
        return "socrates"
    if any(kw in msg for kw in _SCRAP_KEYWORDS):
        return "librarian"
    return None


def _format_memories_with_budget(memories: list[dict], budget: int = CONTEXT_BUDGET_CHARS) -> str:
    """RRF 순위 기반 가변 길이 할당."""
    if not memories:
        return ""
    n = len(memories)
    weights = [1.0 / (i + 1) for i in range(n)]
    total_w = sum(weights)
    allocs = [int(budget * w / total_w) for w in weights]

    lines = []
    for i, mem in enumerate(memories):
        date = mem.get("created_at", "")[:10]
        title = mem.get("title", "Untitled")
        tags = ", ".join(mem.get("tags", []) or [])
        content = mem.get("summary") or mem.get("content", "")
        alloc = allocs[i] if i < len(allocs) else 200
        preview = content[:alloc]

        header = f"--- 기억 #{i + 1} [{date}] {title} ---"
        if tags:
            header += f"\n태그: {tags}"
        lines.append(f"{header}\n{preview}")
    return "\n\n".join(lines)


async def _search_connection_suggestion(
    query: str,
    user_id: str,
    already_referenced_ids: set,
    vector_repo,
) -> dict | None:
    """0.80~0.92 유사도 범위의 연결 후보 반환."""
    try:
        filters = {"user_id": user_id}
        results = await vector_repo.similarity_search(
            query,
            limit=5,
            threshold=CONNECTION_SUGGEST_LOW,
            filters=filters,
        )
        for r in results:
            sim = r.get("similarity", 0)
            if CONNECTION_SUGGEST_LOW <= sim <= CONNECTION_SUGGEST_HIGH and r.get("id") not in already_referenced_ids:
                return r
    except Exception:
        logger.exception("Oracle connection suggestion 실패")
    return None


async def _get_previous_session_context(user_id: UUID, socrates_repo) -> str:
    """이전 세션 요약 컨텍스트 반환."""
    try:
        summaries = await socrates_repo.get_recent_session_summaries(user_id, limit=PREVIOUS_SESSION_LIMIT)
        if not summaries:
            return ""
        lines = []
        for s in reversed(summaries):
            date = str(s["created_at"])[:10]
            title = s.get("title", "")
            lines.append(f"- [{date}] {title}: {s['summary']}")
        return "\n\n**이전 대화 요약:**\n" + "\n".join(lines)
    except Exception:
        logger.exception("Oracle 이전 세션 컨텍스트 조회 실패")
        return ""


async def oracle_enrichment_node(state: SocratesState, runtime: Runtime[AgentContext]) -> dict:
    """Oracle 범용 추가 컨텍스트 수집 + 에이전트 전환 감지 노드.

    1. formatted_memories: graded_memories를 RRF 가변 할당 포맷
    2. connection_suggestion: 3턴 간격 연결 제안
    3. agent_switch_suggestion: 다이어리/스크랩 관련 질문 시 전환 제안 (contradiction_context 활용)
    4. previous_session_context: 첫 턴 이전 세션 요약
    5. user_profile: 개인화 프로필
    """
    writer = get_stream_writer()
    writer({"node": "oracle_enrichment", "status": "started"})

    user_id = state["user_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    turn_count = state.get("turn_count", 0)

    vector_repo = runtime.context.vector_repo
    socrates_repo = runtime.context.socrates_repo

    # 1. 메모리 포맷팅
    formatted_memories = _format_memories_with_budget(graded_memories)

    # 2. 에이전트 전환 제안 감지 (contradiction_context 필드 재활용)
    contradiction_context = ""
    switch_target = _detect_agent_switch_suggestion(user_query)
    if switch_target == "socrates":
        contradiction_context = (
            "[Oracle 제안] 이 주제는 다이어리 뷰의 Socrates 에이전트에서 더 깊은 감정 탐색이 가능합니다."
        )
    elif switch_target == "librarian":
        contradiction_context = (
            "[Oracle 제안] 저장하신 스크랩 탐색은 스크랩 뷰의 Librarian 에이전트에서 더 체계적으로 할 수 있습니다."
        )

    # 3. 연결 제안 (3턴 간격)
    connection_suggestion = ""
    if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
        referenced_ids = {m.get("id") for m in graded_memories}
        suggestion = await _search_connection_suggestion(search_query, user_id, referenced_ids, vector_repo)
        if suggestion:
            date = suggestion.get("created_at", "")[:10]
            title = suggestion.get("title", "Untitled")
            summary = suggestion.get("summary") or suggestion.get("content", "")[:200]
            connection_suggestion = f"[{date}] {title}: {summary}"

    # 4. 이전 세션 컨텍스트 (첫 턴)
    previous_session_context = ""
    if turn_count == 1:
        previous_session_context = await _get_previous_session_context(UUID(user_id), socrates_repo)

    # 5. 사용자 프로필
    user_profile = None
    try:
        from app.services.user_profile_service import get_user_profile

        user_profile = await get_user_profile(user_id)
    except Exception:
        logger.warning("Oracle user_profile 조회 실패")

    writer({"node": "oracle_enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": "",
    }
