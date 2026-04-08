from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProviderInfo(BaseModel):
    """연결된 OAuth 프로바이더 정보."""

    provider: str
    identity_id: str
    email: str | None = None
    created_at: datetime | None = None


class IntegrationStatusResponse(BaseModel):
    """통합 연결 상태 응답."""

    email: str | None = None
    providers: list[ProviderInfo] = []
    kakao_channel: str = "upcoming"
    chrome_extension: str = "upcoming"
    bot_enabled: bool = False
    bot_delivery_hour: int | None = None


class StoreProviderTokenRequest(BaseModel):
    """프로바이더 토큰 저장 요청."""

    provider_token: str = Field(max_length=2000)
    provider_refresh_token: str | None = Field(None, max_length=2000)


# --- 봇 설정 ---


class DeliveryLogEntry(BaseModel):
    """다이제스트 발송 이력 항목."""

    digest_date: date
    status: str
    error_message: str | None = None
    delivered_at: datetime


class BotSettingsResponse(BaseModel):
    """카카오톡 다이제스트 봇 설정 응답."""

    enabled: bool = False
    delivery_hour: int = 21
    include_scraps: bool = True
    include_diaries: bool = True
    include_insights: bool = True
    last_delivery: DeliveryLogEntry | None = None


class BotSettingsUpdateRequest(BaseModel):
    """카카오톡 다이제스트 봇 설정 업데이트 요청."""

    enabled: bool | None = None
    delivery_hour: int | None = None
    include_scraps: bool | None = None
    include_diaries: bool | None = None
    include_insights: bool | None = None

    @field_validator("delivery_hour")
    @classmethod
    def validate_delivery_hour(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 23):
            raise ValueError("delivery_hour must be between 0 and 23")
        return v


# --- 카카오 OpenBuilder 웹훅 ---


class KakaoWebhookUser(BaseModel):
    """카카오 웹훅 사용자 정보."""

    id: str  # botUserKey
    type: str = "botUserKey"
    properties: dict[str, Any] = {}


class KakaoUserRequest(BaseModel):
    """카카오 웹훅 사용자 요청."""

    utterance: str = Field(max_length=10_000)
    user: KakaoWebhookUser


class KakaoWebhookRequest(BaseModel):
    """카카오 OpenBuilder 웹훅 요청."""

    userRequest: KakaoUserRequest
    bot: dict[str, Any] = {}
    action: dict[str, Any] = {}


class KakaoSkillResponse(BaseModel):
    """카카오 스킬 응답."""

    version: str = "2.0"
    template: dict[str, Any]

    @staticmethod
    def simple_text(text: str) -> "KakaoSkillResponse":
        return KakaoSkillResponse(
            template={"outputs": [{"simpleText": {"text": text}}]},
        )


# --- 채널 연동 ---


class ChannelLinkCodeResponse(BaseModel):
    """채널 연결 코드 응답."""

    code: str
    expires_at: datetime
    instructions: str


class ChannelStatusResponse(BaseModel):
    """채널 연결 상태 응답."""

    connected: bool
    bot_user_key: str | None = None
    linked_at: datetime | None = None


class LinkByTokenRequest(BaseModel):
    """토큰 기반 채널 연결 요청."""

    token: str = Field(max_length=500)
