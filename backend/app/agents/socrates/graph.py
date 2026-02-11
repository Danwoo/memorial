from langgraph.graph import END, StateGraph

from app.agents.socrates.nodes.chat import socrates_node
from app.agents.state import AgentState


def create_socrates_graph() -> StateGraph:
    """Socrates 채팅 그래프 생성.

    워크플로우: START -> socrates -> END
    """
    graph = StateGraph(AgentState)

    graph.add_node("socrates", socrates_node)

    graph.set_entry_point("socrates")
    graph.add_edge("socrates", END)

    return graph.compile()


# 싱글톤 인스턴스
socrates_graph = create_socrates_graph()
