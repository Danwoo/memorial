"""
Auth Schemas
Pydantic models for authentication request/response payloads.
"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str  # Supabase validates email format
    password: str


class SignupRequest(BaseModel):
    email: str  # Supabase validates email format
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: str | None = None
    avatar_url: str | None = None
