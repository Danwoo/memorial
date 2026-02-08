"""
Kakao Integration Schemas
Pydantic models for Kakao API request/response payloads.
"""
from pydantic import BaseModel


class KakaoAuthResponse(BaseModel):
    auth_url: str
    message: str


class SendMessageRequest(BaseModel):
    title: str
    content: str
    memory_id: str | None = None


class SendMessageResponse(BaseModel):
    success: bool
    message: str


class KakaoStatusResponse(BaseModel):
    connected: bool
    message: str
