from typing import Literal

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy, RetryPolicy

from app.agents.socrates.context import SocratesContext
from app.agents.socrates.state import SocratesState


def route_after_grading(state: SocratesState) -> Literal["memory_retrieval", "enrichment"]:
    """grading 이후 라우팅. 재시도가 필요하면 memory_retrieval로, 그 외에는 enrichment로.

    context_retrieval은 state에 결과가 이미 있으므로 재실행하지 않는다.
    """
    if state.get("retrieval_quality") == "retry":
        return "memory_retrieval"
    return "enrichment"


def create_socrates_graph() -> StateGraph:
    """Socrates 6노드 파이프라인 그래프 생성 (LangGraph 1.0).

    LangGraph 1.0 기능 총집합:
    - context_schema=SocratesContext: Runtime DI (get_agent_container() 제거)
    - START: v1.0 진입점 상수 (set_entry_point 대신)
    - RetryPolicy: LLM/네트워크 노드 자동 재시도
    - CachePolicy(ttl=60): context_retrieval 노드 결과 캐싱
    - defer=True: grading이 memory_retrieval + context_retrieval 둘 다 완료 대기
    - InMemoryCache: 그래프 레벨 캐시 활성화
    - add_messages: state.py에서 operator.add 대신 사용

    워크플로우:
        START → query_understanding → memory_retrieval  ─┐ (병렬 fan-out)
                                    → context_retrieval ─┤
                                                         ↓
                         grading (defer=True) ───────────┤
                              ↑                           │ retry (threshold 완화)
                              └── memory_retrieval ───────┘
                                                         ↓
                                                    enrichment → context_assembly → END
    """
    from app.agents.socrates.nodes.context_assembly import context_assembly_node
    from app.agents.socrates.nodes.context_retrieval import context_retrieval_node
    from app.agents.socrates.nodes.enrichment import enrichment_node
    from app.agents.socrates.nodes.grading import grading_node
    from app.agents.socrates.nodes.memory_retrieval import memory_retrieval_node
    from app.agents.socrates.nodes.query_understanding import query_understanding_node

    # LLM 노드 재시도 정책: 최대 3회, 지수 백오프
    llm_retry = RetryPolicy(max_attempts=3, initial_interval=1.0)
    # 네트워크 노드 재시도 정책: 최대 2회, 빠른 재시도
    network_retry = RetryPolicy(max_attempts=2, initial_interval=0.5)

    graph = StateGraph(SocratesState, context_schema=SocratesContext)

    graph.add_node("query_understanding", query_understanding_node, retry_policy=llm_retry)
    graph.add_node("memory_retrieval", memory_retrieval_node, retry_policy=network_retry)
    graph.add_node(
        "context_retrieval",
        context_retrieval_node,
        retry_policy=network_retry,
        cache_policy=CachePolicy(ttl=60),  # 60초 캐시 — 같은 사용자 연속 메시지 재활용
    )
    graph.add_node(
        "grading",
        grading_node,
        defer=True,  # memory_retrieval + context_retrieval 완료 후 실행 (fan-in)
        retry_policy=llm_retry,
    )
    graph.add_node("enrichment", enrichment_node, retry_policy=network_retry)
    graph.add_node("context_assembly", context_assembly_node)

    # 진입점 (v1.0 START 상수)
    graph.add_edge(START, "query_understanding")

    # 검색 fan-out (병렬) — query_understanding 완료 후 두 노드 동시 실행
    graph.add_edge("query_understanding", "memory_retrieval")
    graph.add_edge("query_understanding", "context_retrieval")

    # 검색 fan-in → grading (defer=True가 두 브랜치 완료 보장)
    graph.add_edge("memory_retrieval", "grading")
    graph.add_edge("context_retrieval", "grading")

    # grading 조건부 라우팅: retry면 memory_retrieval만 재실행 (context는 state에 이미 있음)
    graph.add_conditional_edges(
        "grading",
        route_after_grading,
        {"memory_retrieval": "memory_retrieval", "enrichment": "enrichment"},
    )

    graph.add_edge("enrichment", "context_assembly")
    graph.add_edge("context_assembly", END)

    return graph.compile(cache=InMemoryCache())  # 그래프 레벨 캐시 활성화


# 싱글톤 인스턴스
socrates_graph = create_socrates_graph()
