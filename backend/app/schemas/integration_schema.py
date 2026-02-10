"""
Integration Schemas
Pydantic models for integration status and provider token storage.
"""

from datetime import datetime

from pydantic import BaseModel


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


class StoreProviderTokenRequest(BaseModel):
    provider_token: str
    provider_refresh_token: str | None = None
