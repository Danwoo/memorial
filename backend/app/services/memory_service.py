"""
Memory Service
Business logic for memory operations
"""
from typing import Optional, List, Tuple
from uuid import UUID

from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.repositories.graph_repository import GraphRepository
from app.schemas.memory import MemoryInDB, SourceType


class MemoryService:
    """Service for memory business logic"""
    
    def __init__(
        self,
        memory_repo: MemoryRepository,
        vector_repo: VectorRepository,
        graph_repo: Optional[GraphRepository] = None
    ):
        self.memory_repo = memory_repo
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo
    
    async def create_memory(
        self,
        user_id: UUID,
        title: str,
        content: str,
        source_type: SourceType,
        source_url: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> MemoryInDB:
        """
        Create a new memory and generate embedding.
        """
        # Create memory record
        memory = await self.memory_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            source_type=source_type,
            source_url=source_url,
            summary=summary,
        )
        
        # Generate and save embedding
        await self.vector_repo.save_embedding(
            memory_id=str(memory.id),
            content=f"{memory.title}\n\n{memory.content}"
        )
        
        return memory
    
    async def get_memory(
        self,
        memory_id: UUID,
        user_id: UUID
    ) -> Optional[MemoryInDB]:
        """Get a memory by ID."""
        return await self.memory_repo.get_by_id(memory_id, user_id)
    
    async def list_memories(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[MemoryInDB], int]:
        """Get paginated list of memories."""
        return await self.memory_repo.get_by_user(
            user_id=user_id,
            page=page,
            limit=limit,
            search=search
        )
    
    async def update_memory_after_processing(
        self,
        memory_id: UUID,
        summary: str,
        tags: List[str],
        entities: Optional[List[dict]] = None,
        relations: Optional[List[dict]] = None,
        source_url: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> bool:
        """
        Update memory after Librarian agent processing.
        Saves summary, tags, and optionally graph data.
        """
        # Update memory status
        success = await self.memory_repo.update_status(
            memory_id=memory_id,
            status="completed",
            summary=summary,
            tags=tags,
            source_url=source_url,
            source_type=source_type
        )
        
        # Save graph data if available
        if self.graph_repo and entities:
            await self.graph_repo.save_entities(entities, str(memory_id))
            
        if self.graph_repo and relations:
            await self.graph_repo.save_relations(relations)
        
        return success
    
    async def delete_memory(
        self,
        memory_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a memory."""
        # TODO: Also delete from Neo4j graph
        return await self.memory_repo.delete(memory_id, user_id)
