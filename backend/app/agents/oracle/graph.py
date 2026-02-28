from app.agents.graph_factory import create_chat_graph
from app.agents.oracle.state import OracleState


def _build_oracle_graph():
    from app.agents.oracle.nodes.oracle_assembly import oracle_assembly_node
    from app.agents.oracle.nodes.oracle_enrichment import oracle_enrichment_node

    return create_chat_graph(
        state_class=OracleState,
        enrichment_node=oracle_enrichment_node,
        assembly_node=oracle_assembly_node,
        enrichment_node_name="oracle_enrichment",
        assembly_node_name="oracle_assembly",
        no_retrieval_target="oracle_enrichment",
    )


# Oracle 그래프 싱글톤
oracle_graph = _build_oracle_graph()


# AgentRegistry 등록
def _register_oracle():
    from app.agents.registry import AgentRegistry

    AgentRegistry.register("oracle", oracle_graph)


_register_oracle()
