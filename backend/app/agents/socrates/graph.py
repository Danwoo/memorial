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


def route_after_grading_socrates(state: SocratesState) -> Literal["memory_retrieval", "emotional_enrichment"]:
    """Socrates 전용 grading 이후 라우팅."""
    if state.get("retrieval_quality") == "retry":
        return "memory_retrieval"
    return "emotional_enrichment"


def create_socrates_graph() -> StateGraph:
    """Oracle/기본 6노드 파이프라인 그래프 생성 (LangGraph 1.0).

    하위호환: 기존 Oracle 대화에 사용. Socrates 전용 그래프는 create_socrates_diary_graph() 사용.

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


def create_socrates_diary_graph():
    """Socrates 다이어리 전문 그래프 생성.

    일반 파이프라인에 diary_deep_retrieval + emotional_enrichment + socrates_assembly 추가.

    워크플로우:
        START → query_understanding → memory_retrieval    ─┐ (병렬 fan-out)
                                    → context_retrieval   ─┤
                                    → diary_deep_retrieval─┤
                                                           ↓
                         grading (defer=True) ─────────────┤
                              ↑                             │ retry
                              └── memory_retrieval ─────────┘
                                                           ↓
                                              emotional_enrichment → socrates_assembly → END
    """
    from app.agents.socrates.nodes.context_retrieval import context_retrieval_node
    from app.agents.socrates.nodes.diary_deep_retrieval import diary_deep_retrieval_node
    from app.agents.socrates.nodes.emotional_enrichment import emotional_enrichment_node
    from app.agents.socrates.nodes.grading import grading_node
    from app.agents.socrates.nodes.memory_retrieval import memory_retrieval_node
    from app.agents.socrates.nodes.query_understanding import query_understanding_node
    from app.agents.socrates.nodes.socrates_assembly import socrates_assembly_node

    llm_retry = RetryPolicy(max_attempts=3, initial_interval=1.0)
    network_retry = RetryPolicy(max_attempts=2, initial_interval=0.5)

    graph = StateGraph(SocratesState, context_schema=SocratesContext)

    graph.add_node("query_understanding", query_understanding_node, retry_policy=llm_retry)
    graph.add_node("memory_retrieval", memory_retrieval_node, retry_policy=network_retry)
    graph.add_node(
        "context_retrieval",
        context_retrieval_node,
        retry_policy=network_retry,
        cache_policy=CachePolicy(ttl=60),
    )
    graph.add_node(
        "diary_deep_retrieval",
        diary_deep_retrieval_node,
        retry_policy=network_retry,
    )
    graph.add_node(
        "grading",
        grading_node,
        defer=True,
        retry_policy=llm_retry,
    )
    graph.add_node("emotional_enrichment", emotional_enrichment_node, retry_policy=network_retry)
    graph.add_node("socrates_assembly", socrates_assembly_node)

    graph.add_edge(START, "query_understanding")
    graph.add_edge("query_understanding", "memory_retrieval")
    graph.add_edge("query_understanding", "context_retrieval")
    graph.add_edge("query_understanding", "diary_deep_retrieval")

    graph.add_edge("memory_retrieval", "grading")
    graph.add_edge("context_retrieval", "grading")
    graph.add_edge("diary_deep_retrieval", "grading")

    graph.add_conditional_edges(
        "grading",
        route_after_grading_socrates,
        {"memory_retrieval": "memory_retrieval", "emotional_enrichment": "emotional_enrichment"},
    )

    graph.add_edge("emotional_enrichment", "socrates_assembly")
    graph.add_edge("socrates_assembly", END)

    return graph.compile(cache=InMemoryCache())


# 싱글톤 인스턴스 (하위호환 유지)
socrates_graph = create_socrates_graph()

# Socrates 다이어리 전문 그래프
socrates_diary_graph = create_socrates_diary_graph()


# AgentRegistry 등록
def _register_socrates():
    from app.agents.registry import AgentRegistry

    AgentRegistry.register("socrates", socrates_diary_graph)


_register_socrates()
