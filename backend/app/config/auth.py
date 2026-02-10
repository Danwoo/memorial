"""
Authentication Dependencies
JWT token verification using Supabase Auth

Dev bypass: When ``Settings.DEBUG`` is ``True`` and no Bearer token is
provided, a default dev user (``DEFAULT_USER_ID``) is returned so the
frontend can operate without a real login.
"""

from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import DEFAULT_USER_ID, get_settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Verify JWT token with Supabase and return user info.

    - Returns ``None`` when no token is provided **and** debug mode is off
      (for optional-auth endpoints).
    - In ``DEBUG`` mode, returns a dev user when no token is provided.
    - Raises ``HTTPException(401)`` when a token is present but invalid.
    """
    settings = get_settings()

    if not credentials:
        # Dev bypass: return mock user so dev frontend works without login
        if settings.DEBUG:
            return {
                "id": DEFAULT_USER_ID,
                "email": "dev@example.com",
                "role": "authenticated",
            }
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

            # Dev bypass: treat invalid/expired tokens as dev user
            if settings.DEBUG:
                return {
                    "id": DEFAULT_USER_ID,
                    "email": "dev@example.com",
                    "role": "authenticated",
                }

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
    except httpx.RequestError:
        if settings.DEBUG:
            return {
                "id": DEFAULT_USER_ID,
                "email": "dev@example.com",
                "role": "authenticated",
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from None


async def require_auth(
    user: dict | None = Depends(get_current_user),
) -> dict:
    """
    Require authentication -- raises 401 if not authenticated.
    Use this for protected endpoints.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_user_id(user: dict = Depends(require_auth)) -> UUID:
    """Extract user ID from authenticated user."""
    return user["id"]
