import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config.auth import get_user_id
from app.config.dependencies import get_duplicate_service
from app.schemas.duplicate_schema import DuplicatesResponse, MergeRequest, MergeResponse
from app.services.duplicate_service import DuplicateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memories/duplicates", tags=["duplicates"])


@router.get("", response_model=DuplicatesResponse)
async def find_duplicates(
    user_id: UUID = Depends(get_user_id),
    service: DuplicateService = Depends(get_duplicate_service),
):
    """사용자 메모리에서 중복 쌍 탐지."""
    pairs = await service.find_duplicates(user_id)
    return DuplicatesResponse(pairs=pairs, total=len(pairs))


@router.post("/merge", response_model=MergeResponse)
async def merge_memories(
    data: MergeRequest,
    user_id: UUID = Depends(get_user_id),
    service: DuplicateService = Depends(get_duplicate_service),
):
    """중복 메모리 병합 (keep_id 유지, merge_id 삭제)."""
    try:
        merged_tags = await service.merge_memories(user_id, data.keep_id, data.merge_id)
        return MergeResponse(kept_id=data.keep_id, merged_tags=merged_tags)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("메모리 병합 실패")
        raise HTTPException(status_code=500, detail=str(e)) from e
