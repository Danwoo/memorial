"""
Librarian Agent - LangGraph Subgraph Definition
Based on Agent_Architecture.md

The Librarian is a background agent that processes ingested content:
1. Curator Node -> Classify & Tag
2. Ontologist Node -> Extract Entities/Relations (if INSIGHT)
3. Save Node -> Persist results

Workflow:
  START -> curator -> (router) -> ontologist -> save -> END
                   |                              ^
                   +-------> save ----------------+
                   |
                   +-------> END (if SPAM)
"""
from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.librarian.nodes import curator_node, ontologist_node, save_node


def route_after_curator(state: AgentState) -> str:
    """
    Conditional edge: Determine next step based on curator's classification.
    """
    next_step = state.get("next_step", "save")
    
    if next_step == "ontologist":
        return "ontologist"
    elif next_step == "end":
        return "end"
    else:
        return "save"


def create_librarian_graph() -> StateGraph:
    """
    Creates the Librarian Subgraph.
    
    Returns a compiled LangGraph that can be invoked with:
        result = await graph.ainvoke(initial_state)
    """
    # Create the graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("curator", curator_node)
    graph.add_node("ontologist", ontologist_node)
    graph.add_node("save", save_node)
    
    # Set entry point
    graph.set_entry_point("curator")
    
    # Add conditional edge from curator
    graph.add_conditional_edges(
        "curator",
        route_after_curator,
        {
            "ontologist": "ontologist",
            "save": "save",
            "end": END
        }
    )
    
    # Ontologist always goes to save
    graph.add_edge("ontologist", "save")
    
    # Save always ends
    graph.add_edge("save", END)
    
    return graph.compile()


# Create singleton instance
librarian_graph = create_librarian_graph()
