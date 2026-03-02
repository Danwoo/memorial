from app.agents.graph_factory import create_chat_graph
from app.agents.socrates.state import SocratesState
from app.config.llm import get_creative_llm


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


# Socrates 다이어리 전문 그래프 (구형 DAG 파이프라인 — 하위호환 유지)
socrates_diary_graph = _build_socrates_graph()


def build_socrates_react_graph():
    """Socrates ReAct 에이전트 그래프를 빌드한다."""
    from app.agents.react_agent import build_react_agent
    from app.agents.socrates.prompts_react import SOCRATES_REACT_SYSTEM_PROMPT
    from app.agents.tools import SOCRATES_TOOLS

    llm = get_creative_llm()
    return build_react_agent(
        llm=llm,
        tools=SOCRATES_TOOLS,
        system_prompt=SOCRATES_REACT_SYSTEM_PROMPT,
    )


# AgentRegistry 등록
def _register_socrates():
    from app.agents.registry import AgentRegistry

    graph = build_socrates_react_graph()
    AgentRegistry.register("socrates", graph)


_register_socrates()
