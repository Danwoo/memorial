import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config.auth import get_user_id
from app.config.dependencies import (
    get_mindmap_insight_service,
    get_mindmap_service,
    get_scrap_repository,
)
from app.repositories.scrap_repository import ScrapRepository
from app.schemas.mindmap_insight_schema import (
    CreateRelationRequest,
    MindmapInsightsResponse,
)
from app.services.mindmap_insight_service import MindmapInsightService
from app.services.mindmap_service import MindmapService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mindmap", tags=["mindmap"])


@router.get("", response_model=dict[str, list[Any]])
async def get_mindmap(
    limit: int = Query(100, ge=1, le=500),
    user_id: UUID = Depends(get_user_id),
    mindmap_service: MindmapService = Depends(get_mindmap_service),
):
    """지식 그래프 시각화 데이터 조회. ``{nodes: [], links: []}`` 형태 반환."""
    if not mindmap_service.is_available:
        return {"nodes": [], "links": []}

    try:
        return await mindmap_service.get_visualization_data(limit, str(user_id))
    except Exception:
        logger.exception("마인드맵 데이터 조회 실패")
        raise HTTPException(status_code=500, detail="Failed to get mindmap data") from None


@router.get("/ego/default", response_model=dict[str, Any])
async def get_ego_default(
    user_id: UUID = Depends(get_user_id),
    mindmap_service: MindmapService = Depends(get_mindmap_service),
):
    """기본 Ego Graph: 연결 수 최다 허브 노드 중심 1-hop 서브그래프."""
    if not mindmap_service.is_available:
        return {"nodes": [], "links": [], "center_node": None}

    try:
        return await mindmap_service.get_ego_default(str(user_id))
    except Exception:
        logger.exception("Ego 그래프 조회 실패")
        raise HTTPException(status_code=500, detail="Failed to get ego graph") from None


@router.get("/ego", response_model=dict[str, Any])
async def get_ego_graph(
    node_name: str = Query(..., min_length=1),
    depth: int = Query(1, ge=1, le=3),
    user_id: UUID = Depends(get_user_id),
    mindmap_service: MindmapService = Depends(get_mindmap_service),
):
    """특정 노드 중심 N-hop Ego Graph 서브그래프 조회."""
    if not mindmap_service.is_available:
        return {"nodes": [], "links": []}

    try:
        return await mindmap_service.get_ego_data(node_name, depth, str(user_id))
    except Exception:
        logger.exception("Ego 서브그래프 조회 실패")
        raise HTTPException(status_code=500, detail="Failed to get ego subgraph") from None


@router.get("/insights", response_model=MindmapInsightsResponse)
async def get_mindmap_insights(
    user_id: UUID = Depends(get_user_id),
    insight_service: MindmapInsightService = Depends(get_mindmap_insight_service),
):
    """마인드맵 인사이트 분석 결과 조회 (클러스터/트렌드/허브/고립 노드)."""
    try:
        return await insight_service.get_insights(str(user_id))
    except Exception:
        logger.exception("마인드맵 인사이트 조회 실패")
        raise HTTPException(status_code=500, detail="Failed to get mindmap insights") from None


@router.post("/rebuild-graph")
async def rebuild_graph(
    user_id: UUID = Depends(get_user_id),
    mindmap_service: MindmapService = Depends(get_mindmap_service),
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
):
    """KuzuDB 그래프를 Supabase 스크랩 데이터로 재구축.

    EC2 이전 등으로 kuzu_data가 비어있을 때 사용.
    LLM 재실행 없이 DB에 저장된 entities/relations만 재인덱싱.
    """
    if not mindmap_service.is_available:
        raise HTTPException(status_code=503, detail="마인드맵 서비스를 사용할 수 없습니다")

    try:
        # Supabase에서 extracted_entities가 있는 모든 스크랩 조회
        raw_scraps = await scrap_repo.get_all_with_entities(user_id, limit=10000)

        processed = 0
        skipped = 0
        for scrap in raw_scraps:
            scrap_id = scrap.get("id")
            entities = scrap.get("extracted_entities") or []
            relations = scrap.get("extracted_relations") or []

            if not scrap_id or not entities:
                skipped += 1
                continue

            await mindmap_service.mindmap_repo.save_entities(entities, str(scrap_id), str(user_id))
            if relations:
                await mindmap_service.mindmap_repo.save_relations(relations)

            processed += 1
            # CPU 블로킹 방지를 위해 10개마다 양보
            if processed % 10 == 0:
                await asyncio.sleep(0)

        logger.info("그래프 재구축 완료: user=%s, processed=%d, skipped=%d", user_id, processed, skipped)
        return {
            "ok": True,
            "processed": processed,
            "skipped": skipped,
            "message": f"{processed}개 스크랩의 그래프 데이터가 재구축되었습니다.",
        }
    except Exception:
        logger.exception("그래프 재구축 실패: user=%s", user_id)
        raise HTTPException(status_code=500, detail="Failed to rebuild graph") from None


@router.post("/relations")
async def create_relation(
    body: CreateRelationRequest,
    user_id: UUID = Depends(get_user_id),
    mindmap_service: MindmapService = Depends(get_mindmap_service),
):
    """수동 관계 생성 (연결 만들기용)."""
    if not mindmap_service.is_available:
        raise HTTPException(status_code=503, detail="마인드맵 서비스를 사용할 수 없습니다")

    try:
        await mindmap_service.create_relation(
            [{"source": body.source, "target": body.target, "type": body.rel_type}],
            user_id=str(user_id),
        )
        return {"ok": True, "message": f"{body.source} → {body.target} 연결 생성됨"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
