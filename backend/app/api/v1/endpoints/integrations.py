"""
Integrations API Endpoints
External service connections (Kakao, etc.)
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

from app.services import kakao

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ========================================
# Schemas
# ========================================
class KakaoAuthResponse(BaseModel):
    auth_url: str
    message: str


class KakaoCallbackResponse(BaseModel):
    success: bool
    message: str


class SendMessageRequest(BaseModel):
    title: str
    content: str
    memory_id: Optional[str] = None


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
    """
    Get Kakao OAuth authorization URL.
    Redirect user to this URL to connect their KakaoTalk.
    """
    auth_url = kakao.get_auth_url()
    return KakaoAuthResponse(
        auth_url=auth_url,
        message="Redirect user to auth_url to connect KakaoTalk"
    )


@router.get("/kakao/callback")
async def kakao_oauth_callback(code: str = Query(...)):
    """
    Handle Kakao OAuth callback.
    Exchanges authorization code for access token.
    """
    try:
        token_data = await kakao.exchange_code_for_token(code)
        
        # In production, store token per user in database
        # For MVP, redirect to success page
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
    """
    Check if Kakao is connected for the current user.
    """
    token = kakao.get_stored_token()
    return KakaoStatusResponse(
        connected=token is not None,
        message="Kakao connected" if token else "Kakao not connected"
    )


@router.post("/kakao/send", response_model=SendMessageResponse)
async def send_kakao_message(request: SendMessageRequest):
    """
    Send a message to user's KakaoTalk "나와의 채팅".
    Requires Kakao to be connected first.
    """
    token = kakao.get_stored_token()
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Kakao not connected. Please authorize first via /kakao/auth"
        )
    
    try:
        await kakao.send_message_to_me(
            access_token=token,
            text=f"📚 {request.title}\n\n{request.content}",
            link_title="Memoir에서 보기",
            link_url=f"http://localhost:5173/memories/{request.memory_id}" if request.memory_id else None
        )
        return SendMessageResponse(
            success=True,
            message="Message sent to KakaoTalk"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


@router.post("/kakao/disconnect")
async def disconnect_kakao():
    """
    Disconnect Kakao (remove stored token).
    """
    kakao.set_stored_token("default_user", None)
    return {"success": True, "message": "Kakao disconnected"}
