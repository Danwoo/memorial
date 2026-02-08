"""
Authentication API Endpoints
Login, logout, and user management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
import httpx

from app.core.config import get_settings
from app.core.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    role: str


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    Returns JWT access token.
    """
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
    """
    Create a new user account.
    Returns JWT access token.
    """
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
            # Check if email confirmation is required
            if data.get("access_token"):
                return AuthResponse(
                    access_token=data["access_token"],
                    user={
                        "id": data["user"]["id"],
                        "email": data["user"]["email"]
                    }
                )
            else:
                # Email confirmation required
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
    """
    Get current user info.
    Requires authentication (token in header).
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return UserResponse(
        id=str(user["id"]),
        email=user["email"],
        role=user.get("role", "authenticated")
    )

