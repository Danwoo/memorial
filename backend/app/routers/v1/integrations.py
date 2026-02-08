"""
Integrations Router
External service connections (Kakao, etc.)
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.services import kakao
from app.services.kakao import _get_default_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ========================================
# Schemas (TODO: Move to schemas/integrations.py)
# ========================================
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


# ========================================
# Kakao Endpoints
# ========================================
@router.get("/kakao/auth", response_model=KakaoAuthResponse)
async def get_kakao_auth_url():
    """Get Kakao OAuth authorization URL."""
    auth_url = kakao.get_auth_url()
    return KakaoAuthResponse(
        auth_url=auth_url,
        message="Redirect user to auth_url to connect KakaoTalk"
    )


@router.get("/kakao/callback")
async def kakao_oauth_callback(code: str = Query(...)):
    """Handle Kakao OAuth callback."""
    try:
        await kakao.exchange_code_for_token(code)
        return RedirectResponse(
            url="http://localhost:5173/settings?kakao=connected",
            status_code=302
        )
    except Exception as e:
        return RedirectResponse(
            url=f"http://localhost:5173/settings?kakao=error&message={str(e)}",
            status_code=302
        )


@router.get("/kakao/status", response_model=KakaoStatusResponse)
async def get_kakao_status():
    """Check if Kakao is connected."""
    service = _get_default_service()
    token = await service.get_stored_token("default_user")
    return KakaoStatusResponse(
        connected=token is not None,
        message="Kakao connected" if token else "Kakao not connected"
    )


@router.post("/kakao/send", response_model=SendMessageResponse)
async def send_kakao_message(request: SendMessageRequest):
    """Send a message to user's KakaoTalk."""
    service = _get_default_service()
    token = await service.get_stored_token("default_user")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Kakao not connected. Please authorize first via /kakao/auth"
        )

    try:
        await service.send_message_to_me(
            access_token=token,
            text=f"📚 {request.title}\n\n{request.content}",
            link_title="Memoir에서 보기",
            link_url=f"http://localhost:5173/memories/{request.memory_id}" if request.memory_id else None
        )
        return SendMessageResponse(success=True, message="Message sent to KakaoTalk")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}") from e


@router.post("/kakao/disconnect")
async def disconnect_kakao():
    """Disconnect Kakao (remove stored token)."""
    kakao.set_stored_token("default_user", None)
    return {"success": True, "message": "Kakao disconnected"}
