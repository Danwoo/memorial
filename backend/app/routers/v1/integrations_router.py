"""
Integrations Router
Account linking status, provider token storage, and KakaoTalk digest bot settings.
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
    BotSettingsResponse,
    BotSettingsUpdateRequest,
    DeliveryLogEntry,
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

            # Fetch bot settings if they exist
            bot_enabled = False
            bot_delivery_hour = None
            try:
                from app.config.database import get_supabase_client

                db = get_supabase_client()
                bot_result = await asyncio.to_thread(
                    lambda: (
                        db.table("kakao_bot_settings")
                        .select("enabled, delivery_hour")
                        .eq("user_id", str(user_id))
                        .execute()
                    )
                )
                if bot_result.data:
                    bot_enabled = bot_result.data[0]["enabled"]
                    bot_delivery_hour = bot_result.data[0]["delivery_hour"]
            except Exception:
                logger.debug("Could not fetch bot settings for status")

            return IntegrationStatusResponse(
                email=user_data.get("email"),
                providers=providers,
                bot_enabled=bot_enabled,
                bot_delivery_hour=bot_delivery_hour,
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


# ─── Bot Settings ─────────────────────────────────────────────────────────────


@router.get("/bot-settings", response_model=BotSettingsResponse)
def get_bot_settings(
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """Get user's KakaoTalk digest bot settings with latest delivery log."""
    try:
        uid = str(user_id)

        settings_result = db.table("kakao_bot_settings").select("*").eq("user_id", uid).execute()

        if settings_result.data:
            data = settings_result.data[0]
            response = BotSettingsResponse(
                enabled=data["enabled"],
                delivery_hour=data["delivery_hour"],
                include_memories=data["include_memories"],
                include_journals=data["include_journals"],
                include_insights=data["include_insights"],
            )
        else:
            response = BotSettingsResponse()

        # Fetch latest delivery log
        log_result = (
            db.table("kakao_delivery_log")
            .select("digest_date, status, error_message, delivered_at")
            .eq("user_id", uid)
            .order("delivered_at", desc=True)
            .limit(1)
            .execute()
        )

        if log_result.data:
            response.last_delivery = DeliveryLogEntry(**log_result.data[0])

        return response
    except Exception as e:
        logger.exception("Failed to fetch bot settings")
        raise HTTPException(status_code=500, detail="Failed to fetch bot settings") from e


@router.put("/bot-settings", response_model=BotSettingsResponse)
def update_bot_settings(
    request: BotSettingsUpdateRequest,
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """Upsert user's KakaoTalk digest bot settings."""
    uid = str(user_id)

    # Build update dict from non-None fields
    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # If enabling, verify kakao_tokens exist
    if update_data.get("enabled"):
        try:
            token_result = db.table("kakao_tokens").select("user_id").eq("user_id", uid).execute()
            if not token_result.data:
                raise HTTPException(
                    status_code=400,
                    detail="카카오 계정 연결이 필요합니다",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to verify kakao token")
            raise HTTPException(status_code=500, detail="Token verification failed") from e

    try:
        # Upsert: include user_id for insert case
        upsert_data = {"user_id": uid, **update_data, "updated_at": "now()"}
        db.table("kakao_bot_settings").upsert(upsert_data, on_conflict="user_id").execute()

        # Return updated settings
        return get_bot_settings(user_id=user_id, db=db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update bot settings")
        raise HTTPException(status_code=500, detail="Failed to update bot settings") from e
