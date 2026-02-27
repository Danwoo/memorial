import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.socrates.context import SocratesContext
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 하이브리드 검색 설정
VECTOR_SEARCH_LIMIT = 5
# dense 검색 임계값 (0.25 이하는 실질적 무관)
DENSE_THRESHOLD = 0.25


async def _fetch_hybrid_memories(
    query: str,
    user_id: str,
    hybrid_search,
    dense_threshold: float = DENSE_THRESHOLD,
    limit: int = VECTOR_SEARCH_LIMIT,
) -> list[dict]:
    """하이브리드 검색 (Dense + Sparse + Graph). 원본 결과 반환."""
    try:
        results = await hybrid_search.search(
            user_id=UUID(user_id),
            query=query,
            limit=limit,
            dense_threshold=dense_threshold,
        )
        return results or []
    except Exception:
        logger.exception("Hybrid search 실패: query=%s", query[:50])
        return []


async def memory_retrieval_node(state: SocratesState, runtime: Runtime[SocratesContext]) -> dict:
    """하이브리드 메모리 검색 전담 노드 (Runtime DI 적용).

    query_understanding과 병렬로 실행되는 context_retrieval과 함께 fan-out 구조 형성.
    grading 노드 (defer=True)가 이 노드와 context_retrieval 둘 다 완료 후 실행된다.

    재시도(retrieval_attempts >= 1) 시 dense_threshold=0.0으로 완화.
    다중 쿼리(rewritten_queries가 2개 이상) 시 각각 검색 후 merge+dedup.
    """
    writer = get_stream_writer()
    writer({"node": "memory_retrieval", "status": "started"})

    user_id = state["user_id"]
    search_query = state.get("search_query", state["user_query"])
    rewritten_queries = state.get("rewritten_queries") or [search_query]
    retrieval_attempts = state.get("retrieval_attempts", 0)

    # 재시도 시 임계값 완화 (grading → memory_retrieval 루프)
    dense_threshold = 0.0 if retrieval_attempts >= 1 else DENSE_THRESHOLD
    hybrid_search = runtime.context.hybrid_search

    # 다중 쿼리 지원 (복합 질의 분해 시)
    if len(rewritten_queries) > 1:
        import asyncio

        all_fetch_tasks = [
            _fetch_hybrid_memories(q, user_id, hybrid_search, dense_threshold) for q in rewritten_queries
        ]
        results_per_query = await asyncio.gather(*all_fetch_tasks, return_exceptions=True)
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
        raw_memories = raw_memories[:VECTOR_SEARCH_LIMIT]
    else:
        raw_memories = await _fetch_hybrid_memories(search_query, user_id, hybrid_search, dense_threshold)

    logger.debug(
        "memory_retrieval: query=%s, memories=%d개, attempts=%d",
        search_query[:50],
        len(raw_memories),
        retrieval_attempts + 1,
    )

    writer(
        {
            "node": "memory_retrieval",
            "status": "done",
            "count": len(raw_memories),
            "attempts": retrieval_attempts + 1,
        }
    )

    return {
        "raw_memories": raw_memories,
        "retrieval_attempts": retrieval_attempts + 1,
    }
