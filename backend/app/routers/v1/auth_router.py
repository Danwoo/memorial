"""
Auth Router
Authentication endpoints (login, signup, user info)
Note: Auth endpoints are pass-through to Supabase Auth, so not using Service layer
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.config.auth import get_current_user
from app.config.settings import get_settings
from app.schemas.auth_schema import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email and password."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": request.email,
                "password": request.password
            }
        )

        if response.status_code == 200:
            data = response.json()
            return AuthResponse(
                access_token=data["access_token"],
                user={
                    "id": data["user"]["id"],
                    "email": data["user"]["email"]
                }
            )
        else:
            error = response.json()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error.get("error_description", "Invalid credentials")
            )


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Create a new user account."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.SUPABASE_URL}/auth/v1/signup",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": request.email,
                "password": request.password
            }
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("access_token"):
                return AuthResponse(
                    access_token=data["access_token"],
                    user={
                        "id": data["user"]["id"],
                        "email": data["user"]["email"]
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_200_OK,
                    detail="Please check your email to confirm your account"
                )
        else:
            error = response.json()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error.get("msg", "Signup failed")
            )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    # Fetch profile data
    settings = get_settings()
    profile = {}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.SUPABASE_URL}/rest/v1/profiles?id=eq.{user['id']}&select=*",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}"
                }
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
        avatar_url=profile.get("avatar_url")
    )
