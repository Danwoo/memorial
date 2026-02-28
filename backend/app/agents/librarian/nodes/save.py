import logging
from uuid import UUID

from app.agents.container import get_agent_container
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


async def save_node(state: AgentState) -> dict:
    """Save 노드: 분석 결과를 DB에 저장하고 그래프 동기화 트리거.

    Args:
        state: classification, tags, summary, entities, relations을 포함한 상태

    Returns:
        next_step = "end"를 포함한 dict
    """
    scrap_id = state.get("target_scrap_id")

    if not scrap_id:
        return {"next_step": "end", "error": "No scrap_id provided"}

    try:
        container = get_agent_container()
        scrap_service = container.scrap_service
        mindmap_repo = container.mindmap_repo

        classification = state.get("classification", "FACT")
        summary = state.get("summary", "")
        tags = state.get("tags", [])

        entities = state.get("extracted_entities", [])
        relations = state.get("extracted_relations", [])

        logger.info(
            "Save node: %d entities, %d relations, mindmap=%s", len(entities), len(relations), mindmap_repo.is_connected
        )

        source_url = state.get("source_url")
        source_type = "WEB" if source_url else None
        user_id = state.get("user_id")

        if classification == "SPAM":
            tags.append("SPAM")
            await scrap_service.update_scrap_after_processing(
                scrap_id=UUID(scrap_id),
                summary="Spam detected",
                tags=tags,
                source_type=source_type,
                user_id=str(user_id) if user_id else None,
            )
        else:
            await scrap_service.update_scrap_after_processing(
                scrap_id=UUID(scrap_id),
                summary=summary,
                tags=tags,
                entities=entities,
                relations=relations,
                source_type=source_type,
                user_id=str(user_id) if user_id else None,
            )

        return {"next_step": "end"}

    except Exception as e:
        return {"next_step": "end", "error": str(e)}
