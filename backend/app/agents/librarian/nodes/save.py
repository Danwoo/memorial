"""
Save Node - Persist processed data to database
Updates memory with classification results and triggers graph sync
"""
from app.agents.state import AgentState
from app.infrastructure.database import get_supabase_client
from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.repositories.graph_repository import GraphRepository
from app.services.memory_service import MemoryService
from uuid import UUID


async def save_node(state: AgentState) -> dict:
    """
    Save Node: Updates memory status and saves analysis results.
    
    Input: state with classification, tags, summary, entities, relations
    Output: next_step = "end"
    """
    memory_id = state.get("target_memory_id")
    
    if not memory_id:
        return {"next_step": "end", "error": "No memory_id provided"}
    
    try:
        # Dependency Injection (Manual)
        db = get_supabase_client()
        memory_repo = MemoryRepository(db)
        vector_repo = VectorRepository(db)
        graph_repo = GraphRepository()
        
        memory_service = MemoryService(memory_repo, vector_repo, graph_repo)
        
        # Prepare data
        classification = state.get("classification", "FACT")
        summary = state.get("summary", "")
        tags = state.get("tags", [])
        
        entities = state.get("extracted_entities", [])
        relations = state.get("extracted_relations", [])
        
        source_url = state.get("source_url")
        source_type = "WEB" if source_url else None
        
        # Determine status
        if classification == "SPAM":
            # For SPAM, we might want to delete or mark as discarded
            # Service currently doesn't simulate "discard" logic in update_memory_after_processing
            # So we might need to handle it or just mark completed with SPAM tag
            tags.append("SPAM")
            await memory_service.update_memory_after_processing(
                memory_id=UUID(memory_id),
                summary="Spam detected",
                tags=tags,
                source_url=source_url,
                source_type=source_type
            )
            # Maybe delete embedding? Service creates embedding on create.
            pass
        else:
            # Normal Flow
            await memory_service.update_memory_after_processing(
                memory_id=UUID(memory_id),
                summary=summary,
                tags=tags,
                entities=entities,
                relations=relations,
                source_url=source_url,
                source_type=source_type
            )
        
        return {"next_step": "end"}
        
    except Exception as e:
        return {"next_step": "end", "error": str(e)}
