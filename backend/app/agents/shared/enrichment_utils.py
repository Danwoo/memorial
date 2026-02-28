import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# 반론 검색 기본 설정
DEFAULT_CONTRADICTION_SEARCH_LIMIT = 2
DEFAULT_CONTRADICTION_THRESHOLD = 0.4
DEFAULT_MAX_CONTRADICTING_RESULTS = 3
# 연결 제안 기본 임계값
DEFAULT_CONNECTION_LOW = 0.80
DEFAULT_CONNECTION_HIGH = 0.92
# 이전 세션 기본 조회 수
DEFAULT_SESSION_CONTEXT_LIMIT = 3
# 컨텍스트 예산 기본값
DEFAULT_CONTEXT_BUDGET_CHARS = 4000


def format_memories_with_budget(
    memories: list[dict],
    budget: int = DEFAULT_CONTEXT_BUDGET_CHARS,
    include_url: bool = False,
    item_label: str = "기억",
) -> str:
    """RRF 순위 기반 가변 길이 할당. 상위 결과에 더 많은 컨텍스트.

    Args:
        memories: 포맷할 메모리/스크랩 목록
        budget: 총 문자 예산
        include_url: True면 source_url 출처 표시 (스크랩용)
        item_label: 항목 레이블 (기억 / 스크랩)
    """
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

        header = f"--- {item_label} #{i + 1} [{date}] {title} ---"
        if tags:
            header += f"\n태그: {tags}"
        if include_url:
            url = mem.get("source_url") or mem.get("url", "")
            if url:
                header += f"\n출처: {url}"
        lines.append(f"{header}\n{preview}")
    return "\n\n".join(lines)


def format_connection_suggestion(suggestion: dict | None, include_url: bool = False) -> str:
    """연결 제안 dict를 표시용 문자열로 변환.

    Args:
        suggestion: search_connection_suggestion 반환값 (None이면 빈 문자열 반환)
        include_url: True면 source_url 출처 표시 (Librarian용)
    """
    if not suggestion:
        return ""
    date = suggestion.get("created_at", "")[:10]
    title = suggestion.get("title", "Untitled")
    summary = suggestion.get("summary") or suggestion.get("content", "")[:200]
    result = f"[{date}] {title}: {summary}"
    if include_url:
        url = suggestion.get("source_url") or suggestion.get("url", "")
        if url:
            result += f" (출처: {url})"
    return result


async def search_connection_suggestion(
    query: str,
    user_id: str,
    already_referenced_ids: set,
    vector_repo,
    low_threshold: float = DEFAULT_CONNECTION_LOW,
    high_threshold: float = DEFAULT_CONNECTION_HIGH,
) -> dict | None:
    """유사도 범위 내 미참조 항목 연결 후보 1개 반환.

    Args:
        query: 검색 쿼리
        user_id: 사용자 ID
        already_referenced_ids: 이미 참조된 ID 집합 (제외 대상)
        vector_repo: 벡터 저장소
        low_threshold: 하한 유사도 (기본 0.80)
        high_threshold: 상한 유사도 (기본 0.92)
    """
    try:
        filters = {"user_id": user_id}
        results = await vector_repo.similarity_search(
            query,
            limit=5,
            threshold=low_threshold,
            filters=filters,
        )
        for r in results:
            sim = r.get("similarity", 0)
            if low_threshold <= sim <= high_threshold and r.get("id") not in already_referenced_ids:
                return r
    except Exception:
        logger.exception("Connection suggestion search 실패")
    return None


async def get_previous_session_context(
    user_id: UUID,
    socrates_repo,
    limit: int = DEFAULT_SESSION_CONTEXT_LIMIT,
    section_title: str = "이전 대화 요약",
) -> str:
    """이전 세션 요약을 컨텍스트 문자열로 조합.

    Args:
        user_id: 사용자 UUID
        socrates_repo: Socrates 저장소
        limit: 조회할 세션 수
        section_title: 섹션 제목 (에이전트별 커스터마이징 가능)
    """
    try:
        summaries = await socrates_repo.get_recent_session_summaries(
            user_id,
            limit=limit,
        )
        if not summaries:
            return ""

        lines = []
        for s in reversed(summaries):
            date = str(s["created_at"])[:10]
            title = s.get("title", "")
            lines.append(f"- [{date}] {title}: {s['summary']}")

        return f"\n\n**{section_title}:**\n" + "\n".join(lines)
    except Exception:
        logger.exception("이전 세션 컨텍스트 조회 실패")
        return ""


async def get_topic_session_context(
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


async def find_contradicting_items(
    query: str,
    current_items: list[dict],
    user_id: str,
    vector_repo,
    search_limit: int = DEFAULT_CONTRADICTION_SEARCH_LIMIT,
    threshold: float = DEFAULT_CONTRADICTION_THRESHOLD,
    query_suffixes: list[str] | None = None,
) -> list[dict]:
    """현재 주제와 반대되는 항목을 벡터 검색으로 탐색.

    Args:
        query: 기본 검색 쿼리
        current_items: 현재 참조 항목 목록 (중복 제외용)
        user_id: 사용자 ID
        vector_repo: 벡터 저장소
        search_limit: 쿼리당 검색 수 제한
        threshold: 유사도 임계값
        query_suffixes: 반론 쿼리 접미사 목록 (기본: ["단점", "비판", "한계", "반대 의견"])
    """
    if query_suffixes is None:
        query_suffixes = ["단점", "비판", "한계", "반대 의견"]

    filters = {"user_id": user_id}
    contradiction_queries = [f"{query} {suffix}" for suffix in query_suffixes]

    current_ids = {m.get("id") for m in current_items}
    contradicting = []
    for cq in contradiction_queries[:search_limit]:
        try:
            results = await vector_repo.similarity_search(
                cq,
                limit=search_limit,
                threshold=threshold,
                filters=filters,
            )
            for r in results:
                if r.get("id") not in current_ids:
                    contradicting.append(r)
        except Exception:
            logger.debug("반론 검색 실패: %s", cq, exc_info=True)

    return contradicting[:DEFAULT_MAX_CONTRADICTING_RESULTS]


async def build_contradiction_context(
    query: str,
    current_items: list[dict],
    user_id: str,
    vector_repo,
    search_limit: int = DEFAULT_CONTRADICTION_SEARCH_LIMIT,
    threshold: float = DEFAULT_CONTRADICTION_THRESHOLD,
    query_suffixes: list[str] | None = None,
) -> str:
    """반론 검색 후 포맷된 컨텍스트 문자열 반환."""
    try:
        contradicting = await find_contradicting_items(
            query,
            current_items,
            user_id,
            vector_repo,
            search_limit=search_limit,
            threshold=threshold,
            query_suffixes=query_suffixes,
        )
        if contradicting:
            return "\n".join(
                f"- [{m.get('created_at', '')[:10]}] {m.get('title', 'Untitled')}: "
                f"{(m.get('summary') or m.get('content', ''))[:200]}"
                for m in contradicting
            )
    except Exception:
        logger.exception("Contradiction context 생성 실패")
    return ""
