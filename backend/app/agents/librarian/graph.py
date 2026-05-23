from langgraph.graph import END, StateGraph

from app.agents.graph_factory import create_chat_graph
from app.agents.librarian.nodes.curator import curator_node
from app.agents.librarian.nodes.ontologist import ontologist_node
from app.agents.librarian.nodes.save import save_node
from app.agents.librarian.state import LibrarianChatState
from app.agents.state import AgentState


def route_after_curator(state: AgentState) -> str:
    """Curator 분류 결과에 따른 조건부 라우팅."""
    next_step = state.get("next_step", "save")

    if next_step == "ontologist":
        return "ontologist"
    if next_step == "end":
        return "end"
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

    graph.add_edge("ontologist", "save")
    graph.add_edge("save", END)

    return graph.compile()


def _build_librarian_chat_graph():
    from app.agents.librarian.nodes.analytical_enrichment import analytical_enrichment_node
    from app.agents.librarian.nodes.knowledge_retrieval import knowledge_retrieval_node
    from app.agents.librarian.nodes.librarian_assembly import librarian_assembly_node

    return create_chat_graph(
        state_class=LibrarianChatState,
        enrichment_node=analytical_enrichment_node,
        assembly_node=librarian_assembly_node,
        enrichment_node_name="analytical_enrichment",
        assembly_node_name="librarian_assembly",
        retrieval_node=knowledge_retrieval_node,
        retrieval_node_name="knowledge_retrieval",
        no_retrieval_target="analytical_enrichment",
    )


# 싱글톤 인스턴스 (콘텐츠 수집 파이프라인)
librarian_graph = create_librarian_graph()

# Librarian 채팅 그래프
librarian_chat_graph = _build_librarian_chat_graph()


def build_librarian_chat_react_graph():
    """Librarian 채팅 ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.librarian.prompts_react import LIBRARIAN_REACT_SYSTEM_PROMPT
    from app.agents.react_agent import build_react_agent
    from app.agents.tools import LIBRARIAN_TOOLS
    from app.config.llm import get_analytical_llm

    llm = get_analytical_llm()
    return build_react_agent(
        llm=llm,
        tools=LIBRARIAN_TOOLS,
        system_prompt=LIBRARIAN_REACT_SYSTEM_PROMPT,
    )


# AgentRegistry 등록 — 채팅 경로는 ReAct를 사용한다
# (librarian_chat_graph는 콘텐츠 수집/legacy DAG용으로 별도 유지)
def _register_librarian():
    from app.agents.registry import AgentRegistry
    from app.agents.streaming import ReactStreaming

    graph = build_librarian_chat_react_graph()
    AgentRegistry.register("librarian", graph=graph, streaming=ReactStreaming())
