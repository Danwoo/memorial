from pydantic import BaseModel


class UserResponse(BaseModel):
    """인증된 사용자 정보 응답."""

    id: str
    email: str
    role: str
    full_name: str | None = None
    avatar_url: str | None = None
