from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.auth import get_user_id
from app.config.dependencies import get_graph_insight_service, get_graph_service
from app.schemas.graph_insight_schema import (
    CreateRelationRequest,
    GraphInsightsResponse,
)
from app.services.graph_insight_service import GraphInsightService
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


@router.get("/ego/default", response_model=dict[str, Any])
async def get_ego_default(
    user_id: UUID = Depends(get_user_id),
    graph_service: GraphService = Depends(get_graph_service),
):
    """기본 Ego Graph: 연결 수 최다 허브 노드 중심 1-hop 서브그래프."""
    if not graph_service.is_available:
        return {"nodes": [], "links": [], "center_node": None}

    try:
        return await graph_service.get_ego_default(str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/ego", response_model=dict[str, Any])
async def get_ego_graph(
    node_name: str = Query(..., min_length=1),
    depth: int = Query(1, ge=1, le=3),
    user_id: UUID = Depends(get_user_id),
    graph_service: GraphService = Depends(get_graph_service),
):
    """특정 노드 중심 N-hop Ego Graph 서브그래프 조회."""
    if not graph_service.is_available:
        return {"nodes": [], "links": []}

    try:
        return await graph_service.get_ego_data(node_name, depth, str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/insights", response_model=GraphInsightsResponse)
async def get_graph_insights(
    user_id: UUID = Depends(get_user_id),
    insight_service: GraphInsightService = Depends(get_graph_insight_service),
):
    """그래프 인사이트 분석 결과 조회 (클러스터/트렌드/허브/고립 노드)."""
    try:
        return await insight_service.get_insights(str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/relations")
async def create_relation(
    body: CreateRelationRequest,
    user_id: UUID = Depends(get_user_id),
    graph_service: GraphService = Depends(get_graph_service),
):
    """수동 관계 생성 (연결 만들기용)."""
    if not graph_service.is_available:
        raise HTTPException(status_code=503, detail="그래프 서비스를 사용할 수 없습니다")

    try:
        await graph_service.create_relation([{"source": body.source, "target": body.target, "type": body.rel_type}])
        return {"ok": True, "message": f"{body.source} → {body.target} 연결 생성됨"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
