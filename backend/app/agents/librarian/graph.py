from typing import Literal

from langgraph.cache.memory import InMemoryCache
from langgraph.graph import END, START, StateGraph
from langgraph.types import CachePolicy, RetryPolicy

from app.agents.librarian.nodes.curator import curator_node
from app.agents.librarian.nodes.ontologist import ontologist_node
from app.agents.librarian.nodes.save import save_node
from app.agents.state import AgentState


def route_after_curator(state: AgentState) -> str:
    """Curator 분류 결과에 따른 조건부 라우팅."""
    next_step = state.get("next_step", "save")

    if next_step == "ontologist":
        return "ontologist"
    elif next_step == "end":
        return "end"
    else:
        return "save"


def create_librarian_graph() -> StateGraph:
    """Librarian 콘텐츠 수집 서브그래프 생성 (스크랩 저장 파이프라인).

    워크플로우:
        START -> curator -> (router) -> ontologist -> save -> END
                         |                              ^
                         +-------> save ----------------+
                         |
                         +-------> END (SPAM인 경우)
    """
    graph = StateGraph(AgentState)

    graph.add_node("curator", curator_node)
    graph.add_node("ontologist", ontologist_node)
    graph.add_node("save", save_node)

    graph.set_entry_point("curator")

    graph.add_conditional_edges(
        "curator", route_after_curator, {"ontologist": "ontologist", "save": "save", "end": END}
    )

    # Ontologist 완료 후 항상 Save로 이동
    graph.add_edge("ontologist", "save")

    # Save 완료 후 종료
    graph.add_edge("save", END)

    return graph.compile()


def route_after_grading_librarian(state) -> Literal["knowledge_retrieval", "analytical_enrichment"]:
    """Librarian 채팅 전용 grading 이후 라우팅."""
    if state.get("retrieval_quality") == "retry":
        return "knowledge_retrieval"
    return "analytical_enrichment"


def create_librarian_chat_graph():
    """Librarian 채팅 그래프 생성 (스크랩 전문 대화 파이프라인).

    워크플로우:
        START → query_understanding → knowledge_retrieval ─┐
                                    → context_retrieval    ─┤
                                                            ↓
                         grading (defer=True) ──────────────┤
                              ↑                              │ retry
                              └── knowledge_retrieval ───────┘
                                                            ↓
                                          analytical_enrichment → librarian_assembly → END
    """
    from app.agents.base_context import AgentContext
    from app.agents.librarian.nodes.analytical_enrichment import analytical_enrichment_node
    from app.agents.librarian.nodes.knowledge_retrieval import knowledge_retrieval_node
    from app.agents.librarian.nodes.librarian_assembly import librarian_assembly_node
    from app.agents.socrates.nodes.context_retrieval import context_retrieval_node
    from app.agents.socrates.nodes.grading import grading_node
    from app.agents.socrates.nodes.query_understanding import query_understanding_node
    from app.agents.socrates.state import SocratesState

    llm_retry = RetryPolicy(max_attempts=3, initial_interval=1.0)
    network_retry = RetryPolicy(max_attempts=2, initial_interval=0.5)

    graph = StateGraph(SocratesState, context_schema=AgentContext)

    graph.add_node("query_understanding", query_understanding_node, retry_policy=llm_retry)
    graph.add_node("knowledge_retrieval", knowledge_retrieval_node, retry_policy=network_retry)
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
    graph.add_node("analytical_enrichment", analytical_enrichment_node, retry_policy=network_retry)
    graph.add_node("librarian_assembly", librarian_assembly_node)

    graph.add_edge(START, "query_understanding")
    graph.add_edge("query_understanding", "knowledge_retrieval")
    graph.add_edge("query_understanding", "context_retrieval")

    graph.add_edge("knowledge_retrieval", "grading")
    graph.add_edge("context_retrieval", "grading")

    graph.add_conditional_edges(
        "grading",
        route_after_grading_librarian,
        {"knowledge_retrieval": "knowledge_retrieval", "analytical_enrichment": "analytical_enrichment"},
    )

    graph.add_edge("analytical_enrichment", "librarian_assembly")
    graph.add_edge("librarian_assembly", END)

    return graph.compile(cache=InMemoryCache())


# 싱글톤 인스턴스 (콘텐츠 수집 파이프라인)
librarian_graph = create_librarian_graph()

# Librarian 채팅 그래프
librarian_chat_graph = create_librarian_chat_graph()


# AgentRegistry 등록
def _register_librarian():
    from app.agents.registry import AgentRegistry

    AgentRegistry.register("librarian", librarian_chat_graph)


_register_librarian()
