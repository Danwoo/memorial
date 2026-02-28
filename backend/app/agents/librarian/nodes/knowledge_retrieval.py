import logging

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 하이브리드 검색 설정
SCRAP_SEARCH_LIMIT = 6
DENSE_THRESHOLD = 0.25
# 태그 기반 클러스터 검색 설정
TAG_CLUSTER_LIMIT = 5


async def _fetch_hybrid_scraps(
    query: str,
    user_id: str,
    hybrid_search,
    dense_threshold: float = DENSE_THRESHOLD,
    limit: int = SCRAP_SEARCH_LIMIT,
) -> list[dict]:
    """하이브리드 검색 (Dense + Sparse + Graph). 스크랩 중심 결과 반환."""
    from uuid import UUID

    try:
        results = await hybrid_search.search(
            user_id=UUID(user_id),
            query=query,
            limit=limit,
            dense_threshold=dense_threshold,
        )
        return results or []
    except Exception:
        logger.exception("Scrap hybrid search 실패: query=%s", query[:50])
        return []


async def _fetch_tag_cluster_context(
    source_context: dict | None,
    user_id: str,
    hybrid_search,
) -> list[dict]:
    """source_context의 태그를 기반으로 관련 스크랩 클러스터 탐색."""
    if not source_context:
        return []
    tags = source_context.get("tags", [])
    if not tags:
        return []

    try:
        from uuid import UUID

        # 태그를 쿼리로 변환하여 검색
        tag_query = " ".join(tags[:3])
        results = await hybrid_search.search(
            user_id=UUID(user_id),
            query=tag_query,
            limit=TAG_CLUSTER_LIMIT,
            dense_threshold=0.3,
        )
        return results or []
    except Exception:
        logger.exception("Tag cluster search 실패")
        return []


async def knowledge_retrieval_node(state: SocratesState, runtime: Runtime[AgentContext]) -> dict:
    """스크랩 전문 지식 검색 노드 (Librarian 에이전트).

    태그 기반 클러스터 검색 + 하이브리드 검색 + 그래프 탐색으로 스크랩 지식 검색.
    grading 노드와 함께 동작하기 위해 raw_memories에 스크랩 검색 결과를 저장한다.
    """
    writer = get_stream_writer()
    writer({"node": "knowledge_retrieval", "status": "started"})

    user_id = state["user_id"]
    search_query = state.get("search_query", state["user_query"])
    rewritten_queries = state.get("rewritten_queries") or [search_query]
    retrieval_attempts = state.get("retrieval_attempts", 0)
    source_context = state.get("source_context")

    dense_threshold = 0.0 if retrieval_attempts >= 1 else DENSE_THRESHOLD
    hybrid_search = runtime.context.hybrid_search

    # 다중 쿼리 하이브리드 검색
    if len(rewritten_queries) > 1:
        import asyncio

        all_tasks = [_fetch_hybrid_scraps(q, user_id, hybrid_search, dense_threshold) for q in rewritten_queries]
        results_per_query = await asyncio.gather(*all_tasks, return_exceptions=True)
        seen_ids: set[str] = set()
        raw_memories: list[dict] = []
        for results in results_per_query:
            if isinstance(results, Exception):
                continue
            for r in results:
                rid = r.get("id", "")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    raw_memories.append(r)
        raw_memories = raw_memories[:SCRAP_SEARCH_LIMIT]
    else:
        raw_memories = await _fetch_hybrid_scraps(search_query, user_id, hybrid_search, dense_threshold)

    # 태그 클러스터 검색 — source_context 태그 활용
    tag_cluster_results = await _fetch_tag_cluster_context(source_context, user_id, hybrid_search)
    for r in tag_cluster_results:
        rid = r.get("id", "")
        if rid and rid not in {m.get("id") for m in raw_memories}:
            raw_memories.append(r)

    raw_memories = raw_memories[:SCRAP_SEARCH_LIMIT]

    logger.debug(
        "knowledge_retrieval: query=%s, scraps=%d개, attempts=%d",
        search_query[:50],
        len(raw_memories),
        retrieval_attempts + 1,
    )

    writer({"node": "knowledge_retrieval", "status": "done", "count": len(raw_memories)})

    return {
        "raw_memories": raw_memories,
        "retrieval_attempts": retrieval_attempts + 1,
    }
