from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config.auth import get_user_id
from app.config.dependencies import get_notification_repository
from app.repositories.notification_repository import (
    VALID_NUDGE_TYPES,
    NotificationRepository,
)
from app.schemas.notification_schema import (
    NotificationSettingsResponse,
    NotificationSettingUpdate,
    NudgeSettingItem,
    PushSubscriptionRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    user_id: UUID = Depends(get_user_id),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """사용자의 알림 설정 조회."""
    rows = repo.get_settings(user_id)
    nudges = [NudgeSettingItem(**row) for row in rows]
    return NotificationSettingsResponse(nudges=nudges)


@router.patch("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    body: NotificationSettingUpdate,
    user_id: UUID = Depends(get_user_id),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """알림 설정 변경 (개별 넛지 타입)."""
    if body.nudge_type not in VALID_NUDGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 넛지 타입: {body.nudge_type}",
        )
    repo.upsert_setting(
        user_id=user_id,
        nudge_type=body.nudge_type,
        enabled=body.enabled,
        delivery_hour=body.delivery_hour,
    )
    # 변경 후 전체 설정 반환
    rows = repo.get_settings(user_id)
    nudges = [NudgeSettingItem(**row) for row in rows]
    return NotificationSettingsResponse(nudges=nudges)


@router.post("/push/subscribe")
async def subscribe_push(
    body: PushSubscriptionRequest,
    user_id: UUID = Depends(get_user_id),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """웹 푸시 구독 등록."""
    repo.save_push_subscription(
        user_id=user_id,
        endpoint=body.endpoint,
        p256dh=body.p256dh,
        auth=body.auth,
    )
    return {"status": "subscribed"}
