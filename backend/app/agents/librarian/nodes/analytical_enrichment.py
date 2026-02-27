import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 컨텍스트 예산
CONTEXT_BUDGET_CHARS = 4000
# 연결 발견 임계값
CONNECTION_SUGGEST_LOW = 0.75
CONNECTION_SUGGEST_HIGH = 0.92
CONNECTION_TURN_INTERVAL = 2  # Librarian은 2턴마다 연결 제안
# 모순 탐지 설정
CONTRADICTION_SEARCH_LIMIT = 3
CONTRADICTION_THRESHOLD = 0.45


def _format_scraps_with_budget(memories: list[dict], budget: int = CONTEXT_BUDGET_CHARS) -> str:
    """RRF 순위 기반 가변 길이 할당. 출처 URL 포함."""
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
        url = mem.get("source_url") or mem.get("url", "")
        alloc = allocs[i] if i < len(allocs) else 200
        preview = content[:alloc]

        header = f"--- 스크랩 #{i + 1} [{date}] {title} ---"
        if tags:
            header += f"\n태그: {tags}"
        if url:
            header += f"\n출처: {url}"
        lines.append(f"{header}\n{preview}")
    return "\n\n".join(lines)


async def _find_contradicting_scraps(
    query: str,
    current_memories: list[dict],
    user_id: str,
    vector_repo,
) -> list[dict]:
    """주제와 반대되는 스크랩을 벡터 검색으로 탐색 (지식 간 모순 발견)."""
    filters = {"user_id": user_id}
    contradiction_queries = [
        f"{query} 비판",
        f"{query} 반론",
        f"{query} 단점",
    ]

    current_ids = {m.get("id") for m in current_memories}
    contradicting = []
    for cq in contradiction_queries[:CONTRADICTION_SEARCH_LIMIT]:
        try:
            results = await vector_repo.similarity_search(
                cq,
                limit=2,
                threshold=CONTRADICTION_THRESHOLD,
                filters=filters,
            )
            for r in results:
                if r.get("id") not in current_ids:
                    contradicting.append(r)
        except Exception:
            pass
    return contradicting[:3]


async def _search_connection_suggestion(
    query: str,
    user_id: str,
    already_referenced_ids: set,
    vector_repo,
) -> dict | None:
    """유사도 0.75~0.92 범위에서 미참조 스크랩 연결 후보 반환."""
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
        logger.exception("Librarian connection suggestion 실패")
    return None


async def _get_previous_session_context(user_id: UUID, socrates_repo) -> str:
    """이전 세션 요약을 컨텍스트로 반환 (Librarian 세션만)."""
    try:
        summaries = await socrates_repo.get_recent_session_summaries(user_id, limit=2)
        if not summaries:
            return ""
        lines = []
        for s in reversed(summaries):
            date = str(s["created_at"])[:10]
            title = s.get("title", "")
            lines.append(f"- [{date}] {title}: {s['summary']}")
        return "\n\n**이전 탐색 요약:**\n" + "\n".join(lines)
    except Exception:
        logger.exception("Librarian 이전 세션 컨텍스트 조회 실패")
        return ""


async def analytical_enrichment_node(state: SocratesState, runtime: Runtime[AgentContext]) -> dict:
    """지식 분석 추가 컨텍스트 수집 노드 (Librarian 에이전트).

    1. formatted_memories: graded_memories를 출처 URL 포함 포맷
    2. contradiction_context: 지식 간 모순 탐지
    3. connection_suggestion: 2턴 간격 연결 발견
    4. previous_session_context: 이전 탐색 세션 요약
    5. user_profile: 관심 태그 기반 개인화
    """
    writer = get_stream_writer()
    writer({"node": "analytical_enrichment", "status": "started"})

    user_id = state["user_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    detected_mode = state.get("detected_mode")
    turn_count = state.get("turn_count", 0)

    vector_repo = runtime.context.vector_repo
    socrates_repo = runtime.context.socrates_repo

    # 1. 스크랩 포맷팅 (출처 URL 포함)
    formatted_memories = _format_scraps_with_budget(graded_memories)

    # 2. 모순 탐지 (compare/connection 모드 또는 기본)
    contradiction_context = ""
    if graded_memories and detected_mode in ("compare", "connection", None):
        try:
            contradicting = await _find_contradicting_scraps(search_query, graded_memories, user_id, vector_repo)
            if contradicting:
                contradiction_context = "\n".join(
                    f"- [{m.get('created_at', '')[:10]}] {m.get('title', 'Untitled')}: "
                    f"{(m.get('summary') or m.get('content', ''))[:200]}"
                    for m in contradicting
                )
        except Exception:
            logger.exception("Librarian 모순 탐지 실패")

    # 3. 연결 제안 (2턴 간격)
    connection_suggestion = ""
    if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
        referenced_ids = {m.get("id") for m in graded_memories}
        suggestion = await _search_connection_suggestion(search_query, user_id, referenced_ids, vector_repo)
        if suggestion:
            date = suggestion.get("created_at", "")[:10]
            title = suggestion.get("title", "Untitled")
            summary = suggestion.get("summary") or suggestion.get("content", "")[:200]
            url = suggestion.get("source_url") or suggestion.get("url", "")
            connection_suggestion = f"[{date}] {title}: {summary}"
            if url:
                connection_suggestion += f" (출처: {url})"

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
        logger.warning("Librarian user_profile 조회 실패")

    writer({"node": "analytical_enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": "",
    }
