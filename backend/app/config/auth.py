from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import get_settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Supabase JWT 토큰을 검증하고 사용자 정보 반환.

    토큰 미제공 시 None 반환 (선택적 인증 엔드포인트용).
    토큰이 유효하지 않으면 401 예외 발생.
    """
    settings = get_settings()

    if not credentials:
        return None

    token = credentials.credentials

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_ANON_KEY,
                },
            )

            if response.status_code == 200:
                user_data = response.json()
                return {
                    "id": UUID(user_data["id"]),
                    "email": user_data.get("email"),
                    "role": user_data.get("role", "authenticated"),
                }

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from None


async def require_auth(
    user: dict | None = Depends(get_current_user),
) -> dict:
    """인증 필수 의존성. 미인증 시 401 발생."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_user_id(user: dict = Depends(require_auth)) -> UUID:
    """인증된 사용자에서 user_id 추출."""
    return user["id"]
