import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.config.auth import get_user_id
from app.config.dependencies import get_export_service
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/scraps")
async def export_scraps(
    user_id: UUID = Depends(get_user_id),
    service: ExportService = Depends(get_export_service),
):
    """사용자의 전체 스크랩을 JSON 파일로 내보내기."""
    data = await service.export_scraps(user_id)

    if not data:
        return Response(
            content=json.dumps([], ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=memoir_scraps.json"},
        )

    content = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=memoir_scraps.json"},
    )


@router.get("/diaries")
async def export_diaries(
    user_id: UUID = Depends(get_user_id),
    service: ExportService = Depends(get_export_service),
):
    """사용자의 전체 다이어리를 Markdown ZIP 파일로 내보내기."""
    zip_bytes = await service.export_diaries_zip(user_id)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=memoir_diaries.zip"},
    )


@router.get("/all")
async def export_all(
    user_id: UUID = Depends(get_user_id),
    service: ExportService = Depends(get_export_service),
):
    """전체 데이터 통합 내보내기 (JSON)."""
    data = await service.export_all(user_id)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=memoir_backup.json"},
    )


@router.get("/counts")
async def export_counts(
    user_id: UUID = Depends(get_user_id),
    service: ExportService = Depends(get_export_service),
):
    """내보내기 미리보기용 데이터 건수 조회."""
    return await service.get_export_counts(user_id)
