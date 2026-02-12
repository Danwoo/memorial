import asyncio
import logging
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from supabase import Client

from app.agents.librarian.graph import librarian_graph
from app.config.auth import get_user_id
from app.config.dependencies import get_db, get_kakao_channel_service
from app.config.settings import get_settings
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
from app.services.kakao_channel_service import KakaoChannelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(user_id: UUID = Depends(get_user_id)):
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
    """카카오 provider_token을 kakao_tokens 테이블에 저장."""
    try:
        expires_in = 21600  # 카카오 기본값: 6시간
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


# --- 봇 설정 ---


@router.get("/bot-settings", response_model=BotSettingsResponse)
def get_bot_settings(
    user_id: UUID = Depends(get_user_id),
    db: Client = Depends(get_db),
):
    """카카오톡 다이제스트 봇 설정 및 최근 발송 이력 조회."""
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
    """카카오톡 다이제스트 봇 설정 upsert."""
    uid = str(user_id)

    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # 활성화 시 카카오 토큰 존재 여부 검증
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
        upsert_data = {"user_id": uid, **update_data, "updated_at": "now()"}
        db.table("kakao_bot_settings").upsert(upsert_data, on_conflict="user_id").execute()

        return get_bot_settings(user_id=user_id, db=db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update bot settings")
        raise HTTPException(status_code=500, detail="Failed to update bot settings") from e


# --- 카카오 OpenBuilder 웹훅 ---


async def _process_with_librarian(
    memory_id: str,
    content: str,
    user_id: str,
) -> None:
    """백그라운드 태스크: Librarian 에이전트로 분류, 태깅, 엔티티 추출."""
    try:
        initial_state = {
            "messages": [],
            "user_id": user_id,
            "context": {},
            "target_memory_id": memory_id,
            "target_text": content,
            "classification": None,
            "summary": None,
            "tags": None,
            "extracted_entities": None,
            "extracted_relations": None,
            "is_streaming": False,
            "next_step": None,
            "error": None,
        }
        result = await librarian_graph.ainvoke(initial_state)
        logger.info(
            "Librarian processed memory %s (via Kakao): classification=%s",
            memory_id,
            result.get("classification"),
        )
    except Exception:
        logger.exception("Librarian error for memory %s (via Kakao)", memory_id)


@router.post("/kakao/webhook")
async def kakao_webhook(
    request: KakaoWebhookRequest,
    background_tasks: BackgroundTasks,
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 OpenBuilder 스킬 웹훅. 인증 불필요 (카카오 서버에서 직접 호출)."""
    try:
        utterance = request.userRequest.utterance
        bot_user_key = request.userRequest.user.id
        plusfriend_user_key = request.userRequest.user.properties.get("plusfriendUserKey")

        response = await channel_service.process_webhook(
            utterance=utterance,
            bot_user_key=bot_user_key,
            plusfriend_user_key=plusfriend_user_key,
        )

        # 신규 저장된 메모리에 대해 Librarian 백그라운드 처리 스케줄링
        user_id = channel_service.lookup_user_id(bot_user_key)
        if user_id and not utterance.startswith("#") and utterance != "#도움말":
            try:
                from app.config.database import get_supabase_client

                db = get_supabase_client()
                latest = (
                    db.table("memories")
                    .select("id, content")
                    .eq("user_id", user_id)
                    .eq("source_type", "KAKAO")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if latest.data:
                    memory = latest.data[0]
                    background_tasks.add_task(
                        _process_with_librarian,
                        memory["id"],
                        memory["content"],
                        user_id,
                    )
            except Exception:
                logger.exception("Failed to schedule Librarian for Kakao memory")

        return response.model_dump()
    except Exception:
        logger.exception("카카오 웹훅 처리 중 오류 발생")
        return KakaoSkillResponse.simple_text("처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.").model_dump()


# --- 채널 연동 관리 ---


@router.post("/kakao/channel/link-code", response_model=ChannelLinkCodeResponse)
def generate_channel_link_code(
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 페어링용 임시 연결 코드 생성."""
    try:
        result = channel_service.generate_link_code(str(user_id))
        return ChannelLinkCodeResponse(**result)
    except Exception as e:
        logger.exception("Failed to generate link code")
        raise HTTPException(status_code=500, detail="Failed to generate link code") from e


@router.get("/kakao/channel/status", response_model=ChannelStatusResponse)
def get_channel_status(
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 연결 상태 확인."""
    try:
        result = channel_service.get_channel_status(str(user_id))
        return ChannelStatusResponse(**result)
    except Exception as e:
        logger.exception("Failed to get channel status")
        raise HTTPException(status_code=500, detail="Failed to get channel status") from e


@router.delete("/kakao/channel/disconnect")
def disconnect_channel(
    user_id: UUID = Depends(get_user_id),
    channel_service: KakaoChannelService = Depends(get_kakao_channel_service),
):
    """카카오 채널 연결 해제 (소프트 삭제)."""
    try:
        success = channel_service.disconnect_channel(str(user_id))
        if not success:
            raise HTTPException(status_code=404, detail="No active channel connection found")
        return {"success": True, "message": "채널 연결이 해제되었습니다"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to disconnect channel")
        raise HTTPException(status_code=500, detail="Failed to disconnect channel") from e
