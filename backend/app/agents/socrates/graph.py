from app.agents.graph_factory import create_chat_graph
from app.agents.socrates.state import SocratesState


def _build_socrates_graph():
    from app.agents.socrates.nodes.emotional_enrichment import emotional_enrichment_node
    from app.agents.socrates.nodes.socrates_assembly import socrates_assembly_node

    return create_chat_graph(
        state_class=SocratesState,
        enrichment_node=emotional_enrichment_node,
        assembly_node=socrates_assembly_node,
        enrichment_node_name="emotional_enrichment",
        assembly_node_name="socrates_assembly",
        include_diary=True,
        no_retrieval_target="emotional_enrichment",
    )


# Socrates 다이어리 전문 그래프
socrates_diary_graph = _build_socrates_graph()


# AgentRegistry 등록
def _register_socrates():
    from app.agents.registry import AgentRegistry

    AgentRegistry.register("socrates", socrates_diary_graph)


_register_socrates()
