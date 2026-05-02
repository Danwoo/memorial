import asyncio
import logging

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

DIARY_CONTEXT_LIMIT = 3
DIARY_PREVIEW_LENGTH = 400


async def _fetch_graphrag_context(query: str, user_id: str, context: AgentContext) -> str:
    """GraphRAGRetrievalService로 Global/Local 검색 후 포맷된 컨텍스트 반환."""
    try:
        result = await context.graphrag_retrieval.retrieve(query, user_id)
        ctx = result.get("context", "")
        mode = result.get("mode", "local")
        if ctx:
            return f"[GraphRAG/{mode}]\n{ctx}"
        return ""
    except Exception:
        logger.exception("GraphRAG context fetch 실패")
        return ""


async def _fetch_diary_context(user_id: str, diary_repo, limit: int = DIARY_CONTEXT_LIMIT) -> str:
    """최근 다이어리 항목 조회. 포맷된 텍스트 반환."""
    try:
        recent_diaries = await diary_repo.get_diaries(user_id, limit=limit)
        if recent_diaries:
            return "\n".join(
                f"- [Diary {diary.get('created_at', '')[:10]}] "
                f"Mood: {diary.get('mood', 'N/A')} | "
                f"Tags: {', '.join(diary.get('tags', []) or [])} — "
                f"{diary.get('content', '')[:DIARY_PREVIEW_LENGTH]}..."
                for diary in recent_diaries
            )
    except Exception:
        logger.exception("Diary context fetch 실패")
    return ""


async def _fetch_community_context(user_id: str, query: str, community_summary) -> str:
    """커뮤니티 요약 중 쿼리와 관련된 것만 필터링하여 반환 (GraphRAG 인덱싱 없을 때 보완)."""
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

        return "\n".join(f"- {s}" for s in relevant[:3])
    except Exception:
        logger.warning("Community context fetch 실패")
        return ""


async def context_retrieval_node(state: SocratesState, runtime: Runtime[AgentContext]) -> dict:
    """보조 컨텍스트 수집 노드 — GraphRAG + Diary + Community 병렬 수집.

    GraphRAGRetrievalService가 쿼리를 global/local로 분류하여
    커뮤니티 map-reduce 또는 엔티티 2-hop 탐색을 실행한다.
    """
    retrieval_plan = state.get("retrieval_plan", "full_rag")
    if retrieval_plan in ("no_retrieval", "simple_search"):
        return {"graph_context": "", "diary_context": "", "community_context": ""}

    writer = get_stream_writer()
    writer({"node": "context_retrieval", "status": "started"})

    user_id = state["user_id"]
    search_query = state.get("search_query", state["user_query"])
    diary_repo = runtime.context.diary_repo
    community_summary = runtime.context.community_summary
    agent_context = runtime.context

    graphrag_ctx, diary_ctx, community_ctx = await asyncio.gather(
        _fetch_graphrag_context(search_query, user_id, agent_context),
        _fetch_diary_context(user_id, diary_repo),
        _fetch_community_context(user_id, search_query, community_summary),
        return_exceptions=True,
    )

    if isinstance(graphrag_ctx, Exception):
        logger.warning("graphrag_context fetch 예외: %s", graphrag_ctx)
        graphrag_ctx = ""
    if isinstance(diary_ctx, Exception):
        logger.warning("diary_context fetch 예외: %s", diary_ctx)
        diary_ctx = ""
    if isinstance(community_ctx, Exception):
        logger.warning("community_context fetch 예외: %s", community_ctx)
        community_ctx = ""

    writer({"node": "context_retrieval", "status": "done"})

    if retrieval_plan == "deep_diary":
        return {
            "graph_context": graphrag_ctx,
            "community_context": community_ctx,
        }

    return {
        "graph_context": graphrag_ctx,
        "diary_context": diary_ctx,
        "community_context": community_ctx,
    }
