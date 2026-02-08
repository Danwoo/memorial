"""
Integrations Router
External service connections (Kakao, etc.)
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config.settings import get_settings
from app.security.auth import get_user_id
from app.services import kakao
from app.services.kakao import _get_default_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ------------------------------------------------------------------
# Schemas (TODO: Move to schemas/integrations.py)
# ------------------------------------------------------------------


class KakaoAuthResponse(BaseModel):
    auth_url: str
    message: str


class SendMessageRequest(BaseModel):
    title: str
    content: str
    memory_id: str | None = None


class SendMessageResponse(BaseModel):
    success: bool
    message: str


class KakaoStatusResponse(BaseModel):
    connected: bool
    message: str


# ------------------------------------------------------------------
# Kakao Endpoints
# ------------------------------------------------------------------


@router.get("/kakao/auth", response_model=KakaoAuthResponse)
async def get_kakao_auth_url(
    user_id: UUID = Depends(get_user_id),
):
    """Get Kakao OAuth authorization URL."""
    auth_url = kakao.get_auth_url()
    return KakaoAuthResponse(
        auth_url=auth_url,
        message="Redirect user to auth_url to connect KakaoTalk",
    )


@router.get("/kakao/callback")
async def kakao_oauth_callback(code: str = Query(...)):
    """Handle Kakao OAuth callback (public -- Kakao redirects here)."""
    settings = get_settings()
    frontend_url = settings.FRONTEND_URL

    try:
        await kakao.exchange_code_for_token(code)
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
):
    """Check if Kakao is connected."""
    service = _get_default_service()
    token = await service.get_stored_token(str(user_id))
    return KakaoStatusResponse(
        connected=token is not None,
        message="Kakao connected" if token else "Kakao not connected",
    )


@router.post("/kakao/send", response_model=SendMessageResponse)
async def send_kakao_message(
    request: SendMessageRequest,
    user_id: UUID = Depends(get_user_id),
):
    """Send a message to user's KakaoTalk."""
    service = _get_default_service()
    token = await service.get_stored_token(str(user_id))

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
        await service.send_message_to_me(
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
):
    """Disconnect Kakao (remove stored token)."""
    service = _get_default_service()
    await service.delete_token(str(user_id))
    return {"success": True, "message": "Kakao disconnected"}
