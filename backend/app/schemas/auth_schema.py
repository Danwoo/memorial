"""
Auth Schemas
Pydantic models for authentication response payloads.
"""

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: str | None = None
    avatar_url: str | None = None
