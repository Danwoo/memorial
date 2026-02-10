"""
Integrations Router
Account linking status and provider token storage.
"""

import asyncio
import logging
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.config.auth import get_user_id
from app.config.dependencies import get_db
from app.config.settings import get_settings
from app.schemas.integration_schema import (
    IntegrationStatusResponse,
    ProviderInfo,
    StoreProviderTokenRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(user_id: UUID = Depends(get_user_id)):
    """Get linked identity providers for the current user via Supabase Admin API."""
    settings = get_settings()

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=500, detail="Service role key not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "apikey": settings.SUPABASE_ANON_KEY,
                },
            )

            if response.status_code != 200:
                logger.error("Supabase admin API error: %s", response.text)
                raise HTTPException(status_code=502, detail="Failed to fetch user info")

            user_data = response.json()
            identities = user_data.get("identities", [])

            providers = [
                ProviderInfo(
                    provider=identity.get("provider", ""),
                    identity_id=identity.get("id", ""),
                    email=identity.get("identity_data", {}).get("email"),
                    created_at=identity.get("created_at"),
                )
                for identity in identities
            ]

            return IntegrationStatusResponse(
                email=user_data.get("email"),
                providers=providers,
            )
    except httpx.RequestError as e:
        logger.exception("Failed to contact Supabase admin API")
        raise HTTPException(status_code=502, detail="Auth service unavailable") from e


@router.post("/store-provider-token")
async def store_provider_token(
    request: StoreProviderTokenRequest,
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """Store Kakao provider_token in kakao_tokens table for Phase 3 channel bot."""
    try:
        expires_in = 21600  # Kakao default: 6 hours
        data = {
            "user_id": str(user_id),
            "access_token": request.provider_token,
            "refresh_token": request.provider_refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "expires_at": int(time.time()) + expires_in,
        }
        await asyncio.to_thread(lambda: db.table("kakao_tokens").upsert(data, on_conflict="user_id").execute())
        return {"success": True, "message": "Provider token stored"}
    except Exception as e:
        logger.exception("Failed to store provider token")
        raise HTTPException(status_code=500, detail="Failed to store token") from e
