"""
Integration Schemas
Pydantic models for integration status, provider token storage,
and KakaoTalk digest bot settings.
"""

from datetime import date, datetime

from pydantic import BaseModel, field_validator


class ProviderInfo(BaseModel):
    provider: str
    identity_id: str
    email: str | None = None
    created_at: datetime | None = None


class IntegrationStatusResponse(BaseModel):
    email: str | None = None
    providers: list[ProviderInfo] = []
    kakao_channel: str = "upcoming"
    chrome_extension: str = "upcoming"
    bot_enabled: bool = False
    bot_delivery_hour: int | None = None


class StoreProviderTokenRequest(BaseModel):
    provider_token: str
    provider_refresh_token: str | None = None


# ─── Bot Settings ─────────────────────────────────────────────────────────────


class DeliveryLogEntry(BaseModel):
    digest_date: date
    status: str
    error_message: str | None = None
    delivered_at: datetime


class BotSettingsResponse(BaseModel):
    enabled: bool = False
    delivery_hour: int = 21
    include_memories: bool = True
    include_journals: bool = True
    include_insights: bool = True
    last_delivery: DeliveryLogEntry | None = None


class BotSettingsUpdateRequest(BaseModel):
    enabled: bool | None = None
    delivery_hour: int | None = None
    include_memories: bool | None = None
    include_journals: bool | None = None
    include_insights: bool | None = None

    @field_validator("delivery_hour")
    @classmethod
    def validate_delivery_hour(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 23):
            raise ValueError("delivery_hour must be between 0 and 23")
        return v
