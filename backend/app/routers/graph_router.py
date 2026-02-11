from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.auth import get_user_id
from app.config.dependencies import get_graph_service
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=dict[str, list[Any]])
async def get_graph(
    limit: int = Query(100, ge=1, le=500),
    user_id: UUID = Depends(get_user_id),
    graph_service: GraphService = Depends(get_graph_service),
):
    """지식 그래프 시각화 데이터 조회. ``{nodes: [], links: []}`` 형태 반환."""
    if not graph_service.is_available:
        return {"nodes": [], "links": []}

    try:
        return await graph_service.get_visualization_data(limit, str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
