import logging
from uuid import UUID

from app.agents.state import AgentState
from app.config.database import get_supabase_client
from app.config.dependencies import get_graph_repository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


async def save_node(state: AgentState) -> dict:
    """Save 노드: 분석 결과를 DB에 저장하고 그래프 동기화 트리거.

    Args:
        state: classification, tags, summary, entities, relations을 포함한 상태

    Returns:
        next_step = "end"를 포함한 dict
    """
    memory_id = state.get("target_memory_id")

    if not memory_id:
        return {"next_step": "end", "error": "No memory_id provided"}

    try:
        db = get_supabase_client()
        memory_repo = MemoryRepository(db)
        vector_repo = VectorRepository(db)
        graph_repo = get_graph_repository()

        memory_service = MemoryService(memory_repo, vector_repo, graph_repo)

        classification = state.get("classification", "FACT")
        summary = state.get("summary", "")
        tags = state.get("tags", [])

        entities = state.get("extracted_entities", [])
        relations = state.get("extracted_relations", [])

        logger.info(
            "Save node: %d entities, %d relations, graph=%s", len(entities), len(relations), graph_repo.is_connected
        )

        source_url = state.get("source_url")
        source_type = "WEB" if source_url else None
        user_id = state.get("user_id")

        if classification == "SPAM":
            tags.append("SPAM")
            await memory_service.update_memory_after_processing(
                memory_id=UUID(memory_id),
                summary="Spam detected",
                tags=tags,
                source_url=source_url,
                source_type=source_type,
                user_id=str(user_id) if user_id else None,
            )
        else:
            await memory_service.update_memory_after_processing(
                memory_id=UUID(memory_id),
                summary=summary,
                tags=tags,
                entities=entities,
                relations=relations,
                source_url=source_url,
                source_type=source_type,
                user_id=str(user_id) if user_id else None,
            )

        return {"next_step": "end"}

    except Exception as e:
        return {"next_step": "end", "error": str(e)}
