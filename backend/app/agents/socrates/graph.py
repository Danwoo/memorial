"""
Socrates Agent - LangGraph Definition
Simple single-node graph for chat responses
"""
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.socrates.nodes import socrates_node


def create_socrates_graph() -> StateGraph:
    """
    Creates the Socrates chat graph.
    
    Simple workflow:
        START -> socrates -> END
    """
    graph = StateGraph(AgentState)
    
    # Add single node
    graph.add_node("socrates", socrates_node)
    
    # Set entry and exit
    graph.set_entry_point("socrates")
    graph.add_edge("socrates", END)
    
    return graph.compile()


# Singleton instance
socrates_graph = create_socrates_graph()
