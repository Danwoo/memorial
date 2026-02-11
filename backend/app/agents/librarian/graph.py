from langgraph.graph import END, StateGraph

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
    """Librarian 서브그래프 생성.

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


# 싱글톤 인스턴스
librarian_graph = create_librarian_graph()
