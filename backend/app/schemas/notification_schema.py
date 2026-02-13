from pydantic import BaseModel, Field


class NudgeSettingItem(BaseModel):
    """개별 넛지 설정 항목."""

    nudge_type: str
    enabled: bool = True
    delivery_hour: int | None = None


class NotificationSettingsResponse(BaseModel):
    """알림 설정 조회 응답."""

    nudges: list[NudgeSettingItem]


class NotificationSettingUpdate(BaseModel):
    """알림 설정 변경 요청."""

    nudge_type: str = Field(..., description="evening_review | weekly_summary | connection_found")
    enabled: bool | None = None
    delivery_hour: int | None = Field(None, ge=0, le=23, description="넛지 발송 시각 (0~23, KST)")


class PushSubscriptionRequest(BaseModel):
    """웹 푸시 구독 등록 요청."""

    endpoint: str
    p256dh: str
    auth: str
