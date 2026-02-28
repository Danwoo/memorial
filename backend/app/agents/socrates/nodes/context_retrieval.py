import asyncio
import logging

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.socrates.context import SocratesContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 그래프/다이어리 설정
GRAPH_CONTEXT_LIMIT = 8
GRAPH_KEYWORD_MIN_LENGTH = 2
GRAPH_MAX_KEYWORDS = 3
JOURNAL_CONTEXT_LIMIT = 3
JOURNAL_PREVIEW_LENGTH = 400


async def _fetch_graph_context(query: str, limit: int = GRAPH_CONTEXT_LIMIT) -> str:
    """지식 그래프에서 관련 엔티티 조회. 포맷된 텍스트 반환."""
    try:
        from app.config.dependencies import get_mindmap_repository

        graph_repo = get_mindmap_repository()
        keywords = [word for word in query.split() if len(word) >= GRAPH_KEYWORD_MIN_LENGTH][:GRAPH_MAX_KEYWORDS]
        graph_results = []
        for keyword in keywords:
            related = await graph_repo.get_related_context(keyword, depth=2)
            graph_results.extend(related)

        if not graph_results:
            return ""

        seen: set[str] = set()
        unique_results = []
        for entity in graph_results:
            name = entity.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_results.append(entity)

        graph_lines = []
        for entity in unique_results[:limit]:
            name = entity.get("name", "")
            label = entity.get("label", "")
            rel = entity.get("rel_type", "RELATED_TO")
            dist = entity.get("distance", 1)
            graph_lines.append(f"- {name} ({label}) -- {rel} (depth: {dist})")
        return "\n".join(graph_lines)
    except Exception:
        logger.exception("Graph context fetch 실패")
        return ""


async def _fetch_diary_context(user_id: str, diary_repo, limit: int = JOURNAL_CONTEXT_LIMIT) -> str:
    """최근 다이어리 항목 조회. 포맷된 텍스트 반환."""
    try:
        recent_diaries = await diary_repo.get_diaries(user_id, limit=limit)
        if recent_diaries:
            return "\n".join(
                f"- [Diary {diary.get('created_at', '')[:10]}] "
                f"Mood: {diary.get('mood', 'N/A')} | "
                f"Tags: {', '.join(diary.get('tags', []) or [])} — "
                f"{diary.get('content', '')[:JOURNAL_PREVIEW_LENGTH]}..."
                for diary in recent_diaries
            )
    except Exception:
        logger.exception("Diary context fetch 실패")
    return ""


async def _fetch_community_context(user_id: str, query: str, community_summary) -> str:
    """커뮤니티 요약 중 쿼리와 관련된 것만 필터링하여 반환."""
    try:
        summaries = await community_summary.get_community_summaries(user_id)
        if not summaries:
            return ""

        query_keywords = {word.lower() for word in query.split() if len(word) >= 2}
        relevant = []
        for s in summaries:
            entity_words = {e.lower() for e in s.get("entities", [])}
            if query_keywords & entity_words:
                relevant.append(s["summary"])

        if not relevant:
            return ""

        return "\n".join(f"- {s}" for s in relevant[:3])
    except Exception:
        logger.warning("Community context fetch 실패")
        return ""


async def context_retrieval_node(state: SocratesState, runtime: Runtime[SocratesContext]) -> dict:
    """보조 컨텍스트 3축 병렬 수집 노드 (Runtime DI + CachePolicy 적용).

    graph + diary + community를 asyncio.gather로 내부 병렬화한다.
    CachePolicy(ttl=60)에 의해 같은 사용자가 60초 내 연속 메시지 시 결과를 재활용한다.

    memory_retrieval과 병렬로 실행되며, grading 노드(defer=True)가 둘 다 완료 후 실행된다.
    """
    writer = get_stream_writer()
    writer({"node": "context_retrieval", "status": "started"})

    user_id = state["user_id"]
    search_query = state.get("search_query", state["user_query"])
    diary_repo = runtime.context.diary_repo
    community_summary = runtime.context.community_summary

    graph_ctx, diary_ctx, community_ctx = await asyncio.gather(
        _fetch_graph_context(search_query),
        _fetch_diary_context(user_id, diary_repo),
        _fetch_community_context(user_id, search_query, community_summary),
        return_exceptions=True,
    )

    # gather 예외 처리
    if isinstance(graph_ctx, Exception):
        logger.warning("graph_context fetch 예외: %s", graph_ctx)
        graph_ctx = ""
    if isinstance(diary_ctx, Exception):
        logger.warning("diary_context fetch 예외: %s", diary_ctx)
        diary_ctx = ""
    if isinstance(community_ctx, Exception):
        logger.warning("community_context fetch 예외: %s", community_ctx)
        community_ctx = ""

    writer({"node": "context_retrieval", "status": "done"})

    return {
        "graph_context": graph_ctx,
        "diary_context": diary_ctx,
        "community_context": community_ctx,
    }
