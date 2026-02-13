import logging

from pywebpush import WebPushException, webpush

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def send_push_notification(
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str,
    url: str | None = None,
) -> bool:
    """웹 푸시 알림 전송."""
    settings = get_settings()
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("VAPID 키가 설정되지 않았습니다")
        return False

    subscription_info = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth},
    }

    import json

    payload = json.dumps({"title": title, "body": body, "url": url or "/"})

    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_MAILTO},
        )
        return True
    except WebPushException as e:
        logger.error("푸시 전송 실패: %s", e)
        return False
