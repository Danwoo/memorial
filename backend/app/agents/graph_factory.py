from collections.abc import Callable

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy, RetryPolicy

from app.agents.base_context import AgentContext
from app.agents.base_state import ChatPipelineState


def create_chat_graph(
    state_class: type,
    enrichment_node: Callable,
    assembly_node: Callable,
    enrichment_node_name: str = "enrichment",
    assembly_node_name: str = "assembly",
    retrieval_node: Callable | None = None,
    retrieval_node_name: str = "memory_retrieval",
    include_diary: bool = False,
    no_retrieval_target: str | None = None,
) -> object:
    """파라미터화된 채팅 그래프 팩토리.

    START → query_understanding → (no_retrieval) → enrichment → assembly → END
                                → (retrieval) → [memory + context (+ diary?)] → grading → enrichment → assembly → END

    Args:
        state_class: 에이전트별 State 클래스 (SocratesState / OracleState / LibrarianChatState)
        enrichment_node: 에이전트 고유 enrichment 노드 함수
        assembly_node: 에이전트 고유 assembly 노드 함수
        enrichment_node_name: enrichment 노드 이름 (그래프 내 식별자)
        assembly_node_name: assembly 노드 이름 (그래프 내 식별자)
        retrieval_node: memory_retrieval 대신 사용할 커스텀 검색 노드 (없으면 기본 memory_retrieval 사용)
        retrieval_node_name: 커스텀 검색 노드 이름
        include_diary: True면 diary_deep_retrieval 노드 포함 (Socrates 전용)
        no_retrieval_target: no_retrieval 플랜 시 라우팅 대상 노드 이름 (기본: enrichment_node_name)
    """
    from app.agents.socrates.nodes.context_retrieval import context_retrieval_node
    from app.agents.socrates.nodes.grading import grading_node
    from app.agents.socrates.nodes.memory_retrieval import memory_retrieval_node
    from app.agents.socrates.nodes.query_understanding import query_understanding_node

    if include_diary:
        from app.agents.socrates.nodes.diary_deep_retrieval import diary_deep_retrieval_node

    # 실제 사용할 검색 노드 결정
    actual_retrieval_node = retrieval_node if retrieval_node is not None else memory_retrieval_node
    actual_retrieval_name = retrieval_node_name if retrieval_node is not None else "memory_retrieval"

    # no_retrieval 라우팅 대상
    no_retrieval_dest = no_retrieval_target or enrichment_node_name

    llm_retry = RetryPolicy(max_attempts=3, initial_interval=1.0)
    network_retry = RetryPolicy(max_attempts=2, initial_interval=0.5)

    graph = StateGraph(state_class, context_schema=AgentContext)

    # 공통 노드 등록
    graph.add_node("query_understanding", query_understanding_node, retry_policy=llm_retry)
    graph.add_node(actual_retrieval_name, actual_retrieval_node, retry_policy=network_retry)
    graph.add_node(
        "context_retrieval",
        context_retrieval_node,
        retry_policy=network_retry,
        cache_policy=CachePolicy(ttl=60),
    )
    graph.add_node(
        "grading",
        grading_node,
        defer=True,
        retry_policy=llm_retry,
    )

    # 다이어리 검색 노드 (Socrates 전용)
    if include_diary:
        graph.add_node("diary_deep_retrieval", diary_deep_retrieval_node, retry_policy=network_retry)

    # 에이전트 고유 노드 등록
    graph.add_node(enrichment_node_name, enrichment_node, retry_policy=network_retry)
    graph.add_node(assembly_node_name, assembly_node)

    # 라우팅 함수 (클로저로 에이전트별 설정 캡처)
    def route_after_understanding(state: ChatPipelineState):
        """query_understanding → retrieval fan-out 또는 no_retrieval 직접 분기."""
        plan = state.get("retrieval_plan", "full_rag")
        if plan == "no_retrieval":
            return no_retrieval_dest
        elif include_diary:
            return [actual_retrieval_name, "context_retrieval", "diary_deep_retrieval"]
        else:
            return [actual_retrieval_name, "context_retrieval"]

    def route_after_grading(state: ChatPipelineState):
        """grading → retry 또는 enrichment 분기."""
        if state.get("retrieval_quality") == "retry":
            return actual_retrieval_name
        return enrichment_node_name

    # 엣지 구성
    graph.add_edge(START, "query_understanding")
    graph.add_conditional_edges("query_understanding", route_after_understanding)

    graph.add_edge(actual_retrieval_name, "grading")
    graph.add_edge("context_retrieval", "grading")
    if include_diary:
        graph.add_edge("diary_deep_retrieval", "grading")

    graph.add_conditional_edges(
        "grading",
        route_after_grading,
        {actual_retrieval_name: actual_retrieval_name, enrichment_node_name: enrichment_node_name},
    )

    graph.add_edge(enrichment_node_name, assembly_node_name)
    graph.add_edge(assembly_node_name, END)

    return graph.compile(cache=InMemoryCache())
