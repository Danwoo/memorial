import logging
from uuid import UUID

import httpx
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def _verify_jwt_local(token: str, secret: str, issuer: str | None = None) -> dict | None:
    """PyJWT로 로컬 검증. 성공 시 사용자 dict, 실패 시 None 반환."""
    try:
        options = {}
        if issuer is None:
            options["verify_iss"] = False
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=issuer,
            options=options,
        )
        return {
            "id": UUID(payload["sub"]),
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
        }
    except (pyjwt.InvalidTokenError, KeyError, ValueError):
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Supabase JWT 토큰을 검증하고 사용자 정보 반환.

    SUPABASE_JWT_SECRET 설정 시 로컬 PyJWT 검증 우선, 실패 시 HTTP 폴백.
    토큰 미제공 시 None 반환 (선택적 인증 엔드포인트용).
    토큰이 유효하지 않으면 401 예외 발생.
    """
    settings = get_settings()

    if not credentials:
        return None

    token = credentials.credentials

    # 로컬 JWT 검증 (secret이 설정된 경우): 실패 시 즉시 거부 (HTTP 폴백 없음)
    # 이유: secret이 있으면 완전한 검증이 가능하므로 실패한 토큰에 두 번째 기회를 주면 안 됨
    if settings.SUPABASE_JWT_SECRET:
        issuer = f"{settings.SUPABASE_URL}/auth/v1"
        result = _verify_jwt_local(token, settings.SUPABASE_JWT_SECRET, issuer)
        if result:
            return result
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # HTTP 폴백: Supabase /auth/v1/user 호출
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
    """인증된 사용자에서 user_id 추출 + 로그 컨텍스트에 부착."""
    from app.observability.context import user_id_var

    uid: UUID = user["id"]
    user_id_var.set(str(uid))
    return uid
