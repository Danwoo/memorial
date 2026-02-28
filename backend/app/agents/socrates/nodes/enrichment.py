import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.socrates.context import SocratesContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 반론 검색 설정
CONTRADICTION_SEARCH_LIMIT = 2
CONTRADICTION_THRESHOLD = 0.4
MAX_CONTRADICTING_RESULTS = 3
# 컨텍스트 예산 (가변 길이 할당)
CONTEXT_BUDGET_CHARS = 4000
# 연결 제안 설정
CONNECTION_SUGGEST_LOW = 0.80
CONNECTION_SUGGEST_HIGH = 0.92
CONNECTION_TURN_INTERVAL = 3
# 이전 세션 컨텍스트 조회 수
PREVIOUS_SESSION_CONTEXT_LIMIT = 3


def _format_memories_with_budget(memories: list[dict], budget: int = CONTEXT_BUDGET_CHARS) -> str:
    """RRF 순위 기반 가변 길이 할당. 상위 결과에 더 많은 컨텍스트."""
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


async def _find_contradicting_memories(
    query: str,
    current_memories: list[dict],
    user_id: str,
    vector_repo,
) -> list[dict]:
    """현재 주제와 반대되는 메모리를 벡터 검색으로 탐색."""
    filters = {"user_id": user_id}

    contradiction_queries = [
        f"{query} 단점",
        f"{query} 비판",
        f"{query} 한계",
        f"{query} 반대 의견",
    ]

    current_ids = {m.get("id") for m in current_memories}
    contradicting = []
    for cq in contradiction_queries[:CONTRADICTION_SEARCH_LIMIT]:
        try:
            results = await vector_repo.similarity_search(
                cq,
                limit=CONTRADICTION_SEARCH_LIMIT,
                threshold=CONTRADICTION_THRESHOLD,
                filters=filters,
            )
            for r in results:
                if r.get("id") not in current_ids:
                    contradicting.append(r)
        except Exception:
            logger.debug("반론 검색 실패: %s", cq, exc_info=True)

    return contradicting[:MAX_CONTRADICTING_RESULTS]


async def _build_contradiction_context(
    query: str,
    current_memories: list[dict],
    user_id: str,
    vector_repo,
) -> str:
    """반론 검색 후 포맷된 컨텍스트 문자열 반환."""
    try:
        contradicting = await _find_contradicting_memories(query, current_memories, user_id, vector_repo)
        if contradicting:
            return "\n".join(
                f"- [{m.get('created_at', '')[:10]}] {m.get('title', 'Untitled')}: "
                f"{(m.get('summary') or m.get('content', ''))[:200]}"
                for m in contradicting
            )
    except Exception:
        logger.exception("Contradiction search 실패")
    return ""


async def _search_connection_suggestion(
    query: str,
    user_id: str,
    already_referenced_ids: set,
    vector_repo,
) -> dict | None:
    """0.80~0.92 유사도 범위에서 이미 참조된 ID를 제외하고 1개 연결 후보 반환."""
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
        logger.exception("Connection suggestion search 실패")
    return None


async def _get_previous_session_context(user_id: UUID, socrates_repo) -> str:
    """이전 세션 요약을 컨텍스트 문자열로 조합."""
    try:
        summaries = await socrates_repo.get_recent_session_summaries(
            user_id,
            limit=PREVIOUS_SESSION_CONTEXT_LIMIT,
        )
        if not summaries:
            return ""

        lines = []
        for s in reversed(summaries):
            date = str(s["created_at"])[:10]
            title = s.get("title", "")
            lines.append(f"- [{date}] {title}: {s['summary']}")

        return "\n\n**이전 대화 요약:**\n" + "\n".join(lines)
    except Exception:
        logger.exception("이전 세션 컨텍스트 조회 실패")
        return ""


async def _get_topic_session_context(
    user_id: UUID,
    tags: list[str],
    session_id: str,
    socrates_repo,
) -> str:
    """같은 주제 태그를 가진 과거 세션 요약을 컨텍스트 문자열로 반환."""
    try:
        past_sessions = await socrates_repo.search_sessions_by_topic(
            user_id,
            tags,
            exclude_session_id=UUID(session_id),
            limit=3,
        )
        if not past_sessions:
            return ""

        lines = []
        for s in past_sessions:
            date = str(s["created_at"])[:10]
            title = s.get("title", "")
            summary = s.get("summary") or "(요약 없음)"
            lines.append(f"- [{date}] {title}: {summary}")

        return (
            "\n\n**이 주제에 대한 과거 대화:**\n"
            + "\n".join(lines)
            + "\n과거 대화를 자연스럽게 언급하여 사용자의 사고 변화를 돌아볼 수 있게 해주세요."
        )
    except Exception:
        logger.exception("주제 기반 세션 컨텍스트 조회 실패")
        return ""


async def enrichment_node(state: SocratesState, runtime: Runtime[SocratesContext]) -> dict:
    """모드별 추가 컨텍스트 수집 + 메모리 포맷팅 노드 (Runtime DI 적용).

    1. formatted_memories: graded_memories를 RRF 가중 할당으로 포맷
    2. contradiction_context: counter 모드일 때 반론 검색
    3. connection_suggestion: turn_count % 3 == 0 일 때 연결 제안
    4. previous_session_context / topic_session_context: 첫 턴일 때만
    5. user_profile: 개인화 프로필 조회
    """
    writer = get_stream_writer()
    writer({"node": "enrichment", "status": "started"})

    user_id = state["user_id"]
    session_id = state["session_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    detected_mode = state.get("detected_mode")
    turn_count = state.get("turn_count", 0)
    source_context = state.get("source_context")

    vector_repo = runtime.context.vector_repo
    socrates_repo = runtime.context.socrates_repo

    # 1. 메모리 포맷팅
    formatted_memories = _format_memories_with_budget(graded_memories)

    # 2. counter 모드 반론 컨텍스트
    contradiction_context = ""
    if detected_mode == "counter" and graded_memories:
        contradiction_context = await _build_contradiction_context(search_query, graded_memories, user_id, vector_repo)

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
            logger.debug("연결 제안 발견: %s", title)

    # 4. 이전 세션 / 주제 세션 컨텍스트 (첫 턴일 때만)
    previous_session_context = ""
    topic_session_context = ""
    if turn_count == 1:
        user_uuid = UUID(user_id)
        previous_session_context = await _get_previous_session_context(user_uuid, socrates_repo)

        if source_context and source_context.get("tags"):
            topic_session_context = await _get_topic_session_context(
                user_uuid,
                source_context["tags"],
                session_id,
                socrates_repo,
            )

    # 5. 사용자 프로필
    user_profile = None
    try:
        from app.services.user_profile_service import get_user_profile

        user_profile = await get_user_profile(user_id)
    except Exception:
        logger.warning("user_profile 조회 실패")

    writer({"node": "enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": topic_session_context,
    }
