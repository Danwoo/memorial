"""
Graph Service
Business logic for knowledge graph operations
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

from app.repositories.graph_repository import GraphRepository


class GraphService:
    """Service for knowledge graph business logic"""
    
    def __init__(self, graph_repo: GraphRepository):
        self.graph_repo = graph_repo
    
    @property
    def is_available(self) -> bool:
        """Check if graph features are available."""
        return self.graph_repo.is_connected
    
    async def save_knowledge_graph(
        self,
        memory_id: str,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]]
    ) -> bool:
        """
        Save extracted entities and relations to the knowledge graph.
        Called by Librarian agent after processing.
        """
        if not self.is_available:
            return False
        
        try:
            await self.graph_repo.save_entities(entities, memory_id)
            await self.graph_repo.save_relations(relations)
            return True
        except Exception as e:
            logger.exception("Error saving to graph")
            return False
    
    async def get_visualization_data(
        self,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get graph data for D3 visualization.
        Returns nodes and links.
        """
        if not self.is_available:
            return {"nodes": [], "links": []}
        
        return await self.graph_repo.get_graph_data(limit)
