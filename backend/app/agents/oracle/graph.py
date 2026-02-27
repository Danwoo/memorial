from typing import Literal

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy, RetryPolicy

from app.agents.base_context import AgentContext
from app.agents.socrates.state import SocratesState


def route_after_grading_oracle(state: SocratesState) -> Literal["memory_retrieval", "oracle_enrichment"]:
    """Oracle 전용 grading 이후 라우팅."""
    if state.get("retrieval_quality") == "retry":
        return "memory_retrieval"
    return "oracle_enrichment"


def create_oracle_graph():
    """Oracle 범용 대화 그래프 생성.

    기존 Socrates 6노드 파이프라인을 재활용하되,
    oracle_enrichment + oracle_assembly로 에이전트 전환 제안 기능을 추가한다.

    워크플로우:
        START → query_understanding → memory_retrieval  ─┐ (병렬 fan-out)
                                    → context_retrieval ─┤
                                                         ↓
                         grading (defer=True) ───────────┤
                              ↑                           │ retry
                              └── memory_retrieval ───────┘
                                                         ↓
                                          oracle_enrichment → oracle_assembly → END
    """
    from app.agents.oracle.nodes.oracle_assembly import oracle_assembly_node
    from app.agents.oracle.nodes.oracle_enrichment import oracle_enrichment_node
    from app.agents.socrates.nodes.context_retrieval import context_retrieval_node
    from app.agents.socrates.nodes.grading import grading_node
    from app.agents.socrates.nodes.memory_retrieval import memory_retrieval_node
    from app.agents.socrates.nodes.query_understanding import query_understanding_node

    llm_retry = RetryPolicy(max_attempts=3, initial_interval=1.0)
    network_retry = RetryPolicy(max_attempts=2, initial_interval=0.5)

    graph = StateGraph(SocratesState, context_schema=AgentContext)

    graph.add_node("query_understanding", query_understanding_node, retry_policy=llm_retry)
    graph.add_node("memory_retrieval", memory_retrieval_node, retry_policy=network_retry)
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
    graph.add_node("oracle_enrichment", oracle_enrichment_node, retry_policy=network_retry)
    graph.add_node("oracle_assembly", oracle_assembly_node)

    graph.add_edge(START, "query_understanding")
    graph.add_edge("query_understanding", "memory_retrieval")
    graph.add_edge("query_understanding", "context_retrieval")

    graph.add_edge("memory_retrieval", "grading")
    graph.add_edge("context_retrieval", "grading")

    graph.add_conditional_edges(
        "grading",
        route_after_grading_oracle,
        {"memory_retrieval": "memory_retrieval", "oracle_enrichment": "oracle_enrichment"},
    )

    graph.add_edge("oracle_enrichment", "oracle_assembly")
    graph.add_edge("oracle_assembly", END)

    return graph.compile(cache=InMemoryCache())


# Oracle 그래프 싱글톤
oracle_graph = create_oracle_graph()


# AgentRegistry 등록
def _register_oracle():
    from app.agents.registry import AgentRegistry

    AgentRegistry.register("oracle", oracle_graph)


_register_oracle()
