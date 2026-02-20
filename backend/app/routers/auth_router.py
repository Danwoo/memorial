import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.auth import get_current_user
from app.config.settings import get_settings
from app.schemas.auth_schema import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer()


@router.get("/me", response_model=UserResponse)
async def get_me(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    user: dict = Depends(get_current_user),
):
    """현재 인증된 사용자 정보 조회."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    settings = get_settings()
    profile = {}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}&select=*",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {credentials.credentials}",
                },
            )
            if response.status_code == 200:
                profiles = response.json()
                if profiles:
                    profile = profiles[0]
    except Exception:
        logger.exception("Failed to fetch profile")

    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        role=user.get("role", "authenticated"),
        full_name=profile.get("full_name"),
        avatar_url=profile.get("avatar_url"),
    )
