"""
Graph Router
API endpoints for knowledge graph visualization
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.auth import get_user_id
from app.config.dependencies import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=dict[str, list[Any]])
async def get_graph(
    mock: bool = Query(True),
    limit: int = Query(100, ge=1, le=500),
    user_id: UUID = Depends(get_user_id),
    graph_service: GraphService = Depends(get_graph_service),
):
    """
    Get graph data for visualization.

    Returns ``{nodes: [], links: []}`` with relationships:
    - Resource <-> Concept (extracted topics)
    - Chat <-> Concept (discussed topics)
    - Resource <-> Chat (when chat references a resource)
    - Memory <-> Entity (extracted entities)
    """
    if mock:
        return await graph_service.build_graph_from_memories(user_id, limit)

    if not graph_service.is_available:
        return {"nodes": [], "links": []}

    try:
        return await graph_service.get_visualization_data(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
