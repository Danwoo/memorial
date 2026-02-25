import asyncio
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from supabase import Client

from app.config.auth import get_user_id
from app.config.dependencies import get_db, get_kakao_channel_service
from app.config.settings import get_settings
from app.routers.scrap_router import _process_with_librarian
from app.schemas.integration_schema import (
    BotSettingsResponse,
    BotSettingsUpdateRequest,
    ChannelLinkCodeResponse,
    ChannelStatusResponse,
    DeliveryLogEntry,
    IntegrationStatusResponse,
    KakaoSkillResponse,
    KakaoWebhookRequest,
    ProviderInfo,
    StoreProviderTokenRequest,
)
from app.services.kakao_channel_service import (
    DISCONNECT_COMMAND,
    HELP_COMMAND,
    KAKAO_PREVIEW_MAX_LENGTH,
    LINK_CODE_PATTERN,
    URL_PATTERN,
    KakaoChannelService,
)

logger = logging.getLogger(__name__)

# 카카오 OAuth 액세스 토큰 기본 만료 시간 (6시간)
KAKAO_TOKEN_EXPIRES_IN_SECONDS = 21600

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """Supabase Admin API로 연결된 ID 프로바이더 목록 조회."""
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

            bot_enabled, bot_delivery_hour = await _fetch_bot_settings(db, user_id)

            return IntegrationStatusResponse(
                email=user_data.get("email"),
                providers=providers,
                bot_enabled=bot_enabled,
                bot_delivery_hour=bot_delivery_hour,
            )
    except httpx.RequestError as e:
        logger.exception("Failed to contact Supabase admin API")
        raise HTTPException(status_code=502, detail="Auth service unavailable") from e


async def _fetch_bot_settings(db: Client, user_id: UUID) -> tuple[bool, int | None]:
    """봇 설정에서 enabled, delivery_hour 조회. 실패 시 기본값 반환."""
    try:
        bot_result = await asyncio.to_thread(
            lambda: (
                db.table("kakao_bot_settings").select("enabled, delivery_hour").eq("user_id", str(user_id)).execute()
            )
        )
        if bot_result.data:
            row = bot_result.data[0]
            return row["enabled"], row["delivery_hour"]
    except Exception:
        logger.debug("Could not fetch bot settings for status")
    return False, None


@router.post("/store-provider-token")
async def store_provider_token(
    request: StoreProviderTokenRequest,
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """카카오 provider_token을 kakao_tokens 테이블에 저장."""
    try:
        data = {
            "user_id": str(user_id),
            "access_token": request.provider_token,
            "refresh_token": request.provider_refresh_token,
            "token_type": "bearer",
            "expires_in": KAKAO_TOKEN_EXPIRES_IN_SECONDS,
            "expires_at": int(time.time()) + KAKAO_TOKEN_EXPIRES_IN_SECONDS,
        }
        await asyncio.to_thread(lambda: db.table("kakao_tokens").upsert(data, on_conflict="user_id").execute())
        return {"success": True, "message": "Provider token stored"}
    except Exception as e:
        logger.exception("Failed to store provider token")
        raise HTTPException(status_code=500, detail="Failed to store token") from e


# --- 봇 설정 ---


@router.get("/bot-settings", response_model=BotSettingsResponse)
async def get_bot_settings(
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """카카오톡 다이제스트 봇 설정 및 최근 발송 이력 조회."""
    try:
        uid = str(user_id)

        settings_result = await asyncio.to_thread(
            lambda: db.table("kakao_bot_settings").select("*").eq("user_id", uid).execute()
        )

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

        log_result = await asyncio.to_thread(
            lambda: (
                db.table("kakao_delivery_log")
                .select("digest_date, status, error_message, delivered_at")
                .eq("user_id", uid)
                .order("delivered_at", desc=True)
                .limit(1)
                .execute()
            )
        )

        if log_result.data:
            response.last_delivery = DeliveryLogEntry(**log_result.data[0])

        return response
    except Exception as e:
        logger.exception("Failed to fetch bot settings")
        raise HTTPException(status_code=500, detail="Failed to fetch bot settings") from e


@router.put("/bot-settings", response_model=BotSettingsResponse)
async def update_bot_settings(
    request: BotSettingsUpdateRequest,
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """카카오톡 다이제스트 봇 설정 upsert."""
    uid = str(user_id)

    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # 활성화 시 카카오 토큰 존재 여부 검증
    if update_data.get("enabled"):
        try:
            token_result = await asyncio.to_thread(
                lambda: db.table("kakao_tokens").select("user_id").eq("user_id", uid).execute()
            )
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
        upsert_data = {"user_id": uid, **update_data, "updated_at": datetime.now(UTC).isoformat()}
        await asyncio.to_thread(
            lambda: db.table("kakao_bot_settings").upsert(upsert_data, on_conflict="user_id").execute()
        )

        return await get_bot_settings(user_id=user_id, db=db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update bot settings")
        raise HTTPException(status_code=500, detail="Failed to update bot settings") from e


# --- 카카오 OpenBuilder 웹훅 ---


@router.post("/kakao/webhook")
async def kakao_webhook(
    request: KakaoWebhookRequest,
    background_tasks: BackgroundTasks,
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 OpenBuilder 스킬 웹훅. 인증 불필요 (카카오 서버에서 직접 호출).

    카카오 OpenBuilder 타임아웃은 5초이므로 응답을 최대한 빠르게 반환해야 한다.
    텍스트/URL 저장은 LLM 호출이 필요해 5초를 초과하므로
    즉시 확인 응답을 반환하고 실제 저장은 BackgroundTasks로 처리한다.
    """
    try:
        utterance = request.userRequest.utterance.strip()
        bot_user_key = request.userRequest.user.id
        plusfriend_user_key = request.userRequest.user.properties.get("plusfriendUserKey")

        # --- 빠른 명령어: 즉시 처리 (DB 조회/업데이트만, 5초 이내 보장) ---
        if utterance == HELP_COMMAND:
            response = await channel_service.process_webhook(utterance, bot_user_key, plusfriend_user_key)
            return response.model_dump()

        link_match = LINK_CODE_PATTERN.match(utterance)
        if link_match:
            response = await channel_service.process_webhook(utterance, bot_user_key, plusfriend_user_key)
            return response.model_dump()

        # 사용자 조회
        user_id = await asyncio.to_thread(channel_service.lookup_user_id, bot_user_key)
        if not user_id:
            response = await asyncio.to_thread(
                channel_service._build_link_required_response, bot_user_key, plusfriend_user_key
            )
            return response.model_dump()

        if utterance == DISCONNECT_COMMAND:
            response = await channel_service.process_webhook(utterance, bot_user_key, plusfriend_user_key)
            return response.model_dump()

        # --- 텍스트/URL: 즉시 응답 + 백그라운드 저장 (LLM 호출 5초 초과 방지) ---
        is_url = URL_PATTERN.match(utterance)
        if is_url:
            background_tasks.add_task(_save_url_in_background, channel_service, utterance, user_id, bot_user_key)
            return KakaoSkillResponse.simple_text(
                "URL 저장 중입니다.\n\nmemoir-knowledge.vercel.app 에서 곧 확인하실 수 있습니다."
            ).model_dump()

        # 일반 텍스트 메모
        preview = (
            utterance[:KAKAO_PREVIEW_MAX_LENGTH] + "..." if len(utterance) > KAKAO_PREVIEW_MAX_LENGTH else utterance
        )
        background_tasks.add_task(_save_text_in_background, channel_service, utterance, user_id, bot_user_key)
        return KakaoSkillResponse.simple_text(
            f"메모 저장 중입니다.\n\n내용: {preview}\nmemoir-knowledge.vercel.app 에서 곧 확인하실 수 있습니다."
        ).model_dump()

    except Exception:
        logger.exception("카카오 웹훅 처리 중 오류 발생")
        return KakaoSkillResponse.simple_text("처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.").model_dump()


async def _save_text_in_background(
    channel_service: KakaoChannelService, text: str, user_id: str, bot_user_key: str
) -> None:
    """백그라운드: 텍스트 메모 저장 + Librarian 처리."""
    try:
        await channel_service._save_text_memory(text, user_id)
        logger.info("카카오 텍스트 메모 백그라운드 저장 완료: user=%s", user_id)
    except Exception:
        logger.exception("카카오 텍스트 메모 백그라운드 저장 실패")
    await _run_librarian_for_kakao(bot_user_key)


async def _save_url_in_background(
    channel_service: KakaoChannelService, url: str, user_id: str, bot_user_key: str
) -> None:
    """백그라운드: URL 크롤링 + 메모리 저장 + Librarian 처리."""
    try:
        await channel_service._save_url_memory(url, user_id)
        logger.info("카카오 URL 메모리 백그라운드 저장 완료: user=%s", user_id)
    except Exception:
        logger.exception("카카오 URL 메모리 백그라운드 저장 실패")
    await _run_librarian_for_kakao(bot_user_key)


async def _run_librarian_for_kakao(bot_user_key: str) -> None:
    """백그라운드: 카카오 메모리에 대해 user_id 조회 후 Librarian 처리."""
    try:
        from app.config.database import get_supabase_client

        db = get_supabase_client()
        result = (
            db.table("kakao_channel_mappings")
            .select("user_id")
            .eq("bot_user_key", bot_user_key)
            .eq("channel_status", "active")
            .limit(1)
            .execute()
        )
        if not result.data:
            return
        user_id = result.data[0]["user_id"]

        latest = (
            db.table("scraps")
            .select("id, content")
            .eq("user_id", user_id)
            .eq("source_type", "KAKAO")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not latest.data:
            return

        memory = latest.data[0]
        await _process_with_librarian(memory["id"], memory["content"], user_id)
    except Exception:
        logger.exception("Failed to run Librarian for Kakao memory")


# --- 채널 연동 관리 ---


@router.post("/kakao/channel/link-code", response_model=ChannelLinkCodeResponse)
async def generate_channel_link_code(
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 페어링용 임시 연결 코드 생성."""
    try:
        result = await asyncio.to_thread(channel_service.generate_link_code, str(user_id))
        return ChannelLinkCodeResponse(**result)
    except Exception as e:
        logger.exception("Failed to generate link code")
        raise HTTPException(status_code=500, detail="Failed to generate link code") from e


@router.get("/kakao/channel/status", response_model=ChannelStatusResponse)
async def get_channel_status(
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 연결 상태 확인."""
    try:
        result = await asyncio.to_thread(channel_service.get_channel_status, str(user_id))
        return ChannelStatusResponse(**result)
    except Exception as e:
        logger.exception("Failed to get channel status")
        raise HTTPException(status_code=500, detail="Failed to get channel status") from e


@router.post("/kakao/channel/link-by-token")
async def complete_link_by_token(
    body: dict,
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 토큰 기반 연결 완료. 카카오톡에서 받은 링크로 웹에서 호출."""
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="token is required")
    try:
        result = await asyncio.to_thread(channel_service.complete_link_by_token, token, str(user_id))
        if not result["success"]:
            error_messages = {
                "invalid_token": "유효하지 않은 토큰입니다.",
                "already_used": "이미 사용된 토큰입니다.",
                "expired": "만료된 토큰입니다. 카카오톡에서 다시 메시지를 보내주세요.",
            }
            raise HTTPException(status_code=400, detail=error_messages.get(result["error"], "연결에 실패했습니다."))
        return {"success": True, "message": "카카오톡 채널이 연결되었습니다!"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to complete link by token")
        raise HTTPException(status_code=500, detail="Failed to complete link") from e


@router.delete("/kakao/channel/disconnect")
async def disconnect_channel(
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 연결 해제 (소프트 삭제)."""
    try:
        success = await asyncio.to_thread(channel_service.disconnect_channel, str(user_id))
        if not success:
            raise HTTPException(status_code=404, detail="No active channel connection found")
        return {"success": True, "message": "채널 연결이 해제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to disconnect channel")
        raise HTTPException(status_code=500, detail="Failed to disconnect channel") from e
