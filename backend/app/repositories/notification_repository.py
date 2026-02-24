import logging
from datetime import UTC, datetime
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)

VALID_NUDGE_TYPES = {"evening_review", "weekly_summary", "connection_found"}

DEFAULT_SETTINGS = [
    {"nudge_type": "evening_review", "enabled": True, "delivery_hour": 21},
    {"nudge_type": "weekly_summary", "enabled": True, "delivery_hour": None},
    {"nudge_type": "connection_found", "enabled": True, "delivery_hour": None},
]


class NotificationRepository:
    """알림 설정 및 푸시 구독 관리 리포지토리."""

    def __init__(self, db: Client) -> None:
        self.db = db

    def get_settings(self, user_id: UUID) -> list[dict]:
        """사용자의 넛지 설정 목록 조회. 없으면 기본값 반환."""
        result = (
            self.db.table("notification_settings")
            .select("nudge_type, enabled, delivery_hour")
            .eq("user_id", str(user_id))
            .execute()
        )
        if result.data:
            return result.data

        # 설정이 없으면 기본값 삽입 후 반환
        rows = [{"user_id": str(user_id), **setting} for setting in DEFAULT_SETTINGS]
        self.db.table("notification_settings").insert(rows).execute()
        return DEFAULT_SETTINGS

    def upsert_setting(
        self,
        user_id: UUID,
        nudge_type: str,
        enabled: bool | None = None,
        delivery_hour: int | None = None,
    ) -> dict:
        """넛지 설정 업데이트 (upsert)."""
        update_data: dict = {"user_id": str(user_id), "nudge_type": nudge_type}
        if enabled is not None:
            update_data["enabled"] = enabled
        if delivery_hour is not None:
            update_data["delivery_hour"] = delivery_hour
        update_data["updated_at"] = datetime.now(UTC).isoformat()

        result = self.db.table("notification_settings").upsert(update_data, on_conflict="user_id,nudge_type").execute()
        return result.data[0] if result.data else update_data

    def save_push_subscription(self, user_id: UUID, endpoint: str, p256dh: str, auth: str) -> dict:
        """웹 푸시 구독 정보 저장 (upsert)."""
        data = {
            "user_id": str(user_id),
            "endpoint": endpoint,
            "p256dh": p256dh,
            "auth": auth,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = self.db.table("push_subscriptions").upsert(data, on_conflict="user_id,endpoint").execute()
        return result.data[0] if result.data else data

    def get_push_subscriptions(self, user_id: UUID) -> list[dict]:
        """사용자의 푸시 구독 목록 조회."""
        result = (
            self.db.table("push_subscriptions").select("endpoint, p256dh, auth").eq("user_id", str(user_id)).execute()
        )
        return result.data or []

    def delete_push_subscriptions(self, user_id: UUID) -> None:
        """사용자의 모든 푸시 구독 삭제."""
        self.db.table("push_subscriptions").delete().eq("user_id", str(user_id)).execute()

    def log_notification(
        self,
        user_id: str,
        nudge_type: str,
        content: str,
        status: str = "sent",
    ) -> None:
        """알림 전송 로그 기록."""
        try:
            self.db.table("notification_log").insert(
                {
                    "user_id": user_id,
                    "nudge_type": nudge_type,
                    "content": content,
                    "status": status,
                    "sent_at": datetime.now(UTC).isoformat(),
                }
            ).execute()
        except Exception:
            logger.exception("알림 로그 기록 실패: user_id=%s", user_id[:8])
