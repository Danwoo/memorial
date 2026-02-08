"""
Authentication Dependencies
JWT token verification using Supabase Auth
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
import httpx

from app.core.config import get_settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Verify JWT token with Supabase and return user info.
    Returns None if no token provided (for optional auth).
    Raises HTTPException if token is invalid.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    settings = get_settings()
    
    try:
        # Verify token with Supabase
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_ANON_KEY
                }
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "id": UUID(user_data["id"]),
                    "email": user_data.get("email"),
                    "role": user_data.get("role", "authenticated")
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )


async def require_auth(
    user: Optional[dict] = Depends(get_current_user)
) -> dict:
    """
    Require authentication - raises 401 if not authenticated.
    Use this for protected endpoints.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def get_user_id(user: dict = Depends(require_auth)) -> UUID:
    """Extract user ID from authenticated user."""
    return user["id"]
