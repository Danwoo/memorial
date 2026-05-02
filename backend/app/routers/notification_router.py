from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config.auth import get_user_id
from app.config.dependencies import get_notification_repository
from app.config.settings import get_settings
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


@router.delete("/push/unsubscribe")
async def unsubscribe_push(
    user_id: UUID = Depends(get_user_id),
    repo: NotificationRepository = Depends(get_notification_repository),
):
    """웹 푸시 구독 해제."""
    repo.delete_push_subscriptions(user_id)
    return {"status": "unsubscribed"}


@router.get("/push/vapid-key")
async def get_vapid_public_key():
    """VAPID 공개키 반환 (Service Worker 등록에 필요)."""
    settings = get_settings()
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push not configured")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}


@router.post("/nudge/trigger/{nudge_type}")
async def trigger_nudge(
    nudge_type: str,
    user_id: UUID = Depends(get_user_id),
):
    """넛지 수동 트리거 (테스트/디버그용)."""
    if not get_settings().DEBUG:
        raise HTTPException(status_code=403, detail="Not available in production")

    from app.services.nudge_service import (
        _get_repos,
        _send_nudge_to_user,
    )

    if nudge_type not in VALID_NUDGE_TYPES:
        raise HTTPException(status_code=400, detail=f"유효하지 않은 넛지 타입: {nudge_type}")

    notif_repo, _, _ = _get_repos()
    messages = {
        "evening_review": ("오늘의 회고", "테스트: 오늘의 기억을 돌아보세요.", "/diary"),
        "weekly_summary": ("주간 요약", "테스트: 이번 주 활동을 확인하세요.", "/calendar"),
        "connection_found": ("기억 연결 발견", "테스트: 새로운 연결이 발견되었습니다.", "/mindmap"),
    }
    title, body, url = messages[nudge_type]
    sent = await _send_nudge_to_user(
        notif_repo,
        str(user_id),
        nudge_type,
        title,
        body,
        url=url,
    )
    return {"status": "sent" if sent else "no_subscription", "nudge_type": nudge_type}
