from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from app.services.graph_store import graph_store

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("", response_model=Dict[str, List[Any]])
async def get_graph(limit: int = 100):
    """
    Get graph data for visualization.
    Returns {nodes: [], links: []}
    """
    if not graph_store.graph:
        # Return empty if not connected, to avoid frontend breaking
        return {"nodes": [], "links": []}
        
    try:
        data = await graph_store.get_graph_data(limit=limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
