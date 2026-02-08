"""
Integrations Router
External service connections (Kakao, etc.)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config.auth import get_user_id
from app.config.dependencies import get_kakao_service
from app.config.settings import get_settings
from app.schemas.kakao_schema import (
    KakaoAuthResponse,
    KakaoStatusResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.kakao_service import KakaoService

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ------------------------------------------------------------------
# Kakao Endpoints
# ------------------------------------------------------------------


@router.get("/kakao/auth", response_model=KakaoAuthResponse)
async def get_kakao_auth_url(
    user_id: UUID = Depends(get_user_id),
    kakao_service: KakaoService = Depends(get_kakao_service),
):
    """Get Kakao OAuth authorization URL."""
    auth_url = kakao_service.get_auth_url()
    return KakaoAuthResponse(
        auth_url=auth_url,
        message="Redirect user to auth_url to connect KakaoTalk",
    )


@router.get("/kakao/callback")
async def kakao_oauth_callback(
    code: str = Query(...),
    kakao_service: KakaoService = Depends(get_kakao_service),
):
    """Handle Kakao OAuth callback (public -- Kakao redirects here)."""
    settings = get_settings()
    frontend_url = settings.FRONTEND_URL

    try:
        await kakao_service.exchange_code_for_token(code, "default_user")
        return RedirectResponse(
            url=f"{frontend_url}/settings?kakao=connected",
            status_code=302,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{frontend_url}/settings?kakao=error&message={e!s}",
            status_code=302,
        )


@router.get("/kakao/status", response_model=KakaoStatusResponse)
async def get_kakao_status(
    user_id: UUID = Depends(get_user_id),
    kakao_service: KakaoService = Depends(get_kakao_service),
):
    """Check if Kakao is connected."""
    token = await kakao_service.get_stored_token(str(user_id))
    return KakaoStatusResponse(
        connected=token is not None,
        message="Kakao connected" if token else "Kakao not connected",
    )


@router.post("/kakao/send", response_model=SendMessageResponse)
async def send_kakao_message(
    request: SendMessageRequest,
    user_id: UUID = Depends(get_user_id),
    kakao_service: KakaoService = Depends(get_kakao_service),
):
    """Send a message to user's KakaoTalk."""
    token = await kakao_service.get_stored_token(str(user_id))

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Kakao not connected. Please authorize first via /kakao/auth",
        )

    settings = get_settings()
    frontend_url = settings.FRONTEND_URL
    link_url = (
        f"{frontend_url}/memories/{request.memory_id}"
        if request.memory_id
        else None
    )

    try:
        await kakao_service.send_message_to_me(
            access_token=token,
            text=f"{request.title}\n\n{request.content}",
            link_title="Memoir에서 보기",
            link_url=link_url,
        )
        return SendMessageResponse(success=True, message="Message sent to KakaoTalk")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to send message: {e!s}"
        ) from e


@router.post("/kakao/disconnect")
async def disconnect_kakao(
    user_id: UUID = Depends(get_user_id),
    kakao_service: KakaoService = Depends(get_kakao_service),
):
    """Disconnect Kakao (remove stored token)."""
    await kakao_service.delete_token(str(user_id))
    return {"success": True, "message": "Kakao disconnected"}
