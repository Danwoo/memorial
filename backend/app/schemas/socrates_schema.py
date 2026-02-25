from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SocratesSessionCreate(BaseModel):
    """소크라테스 세션 생성 요청."""

    title: str | None = None


class SocratesSessionResponse(BaseModel):
    """소크라테스 세션 상세 응답."""

    id: UUID
    title: str
    created_at: datetime


class SocratesSessionUpdate(BaseModel):
    """소크라테스 세션 수정 요청."""

    title: str


class SocratesMessageRequest(BaseModel):
    """소크라테스 메시지 전송 요청."""

    content: str
    mode: str | None = None  # insight, counter, summary, evening


class SocratesMessageResponse(BaseModel):
    """소크라테스 이력의 단일 메시지."""

    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


class SocratesStreamEvent(BaseModel):
    """소크라테스 스트리밍 SSE 이벤트."""

    content: str | None = None
    done: bool | None = None
    error: str | None = None


class SocratesHistoryResponse(BaseModel):
    """소크라테스 이력 응답."""

    session_id: UUID
    messages: list[SocratesMessageResponse]


class SocratesFeedbackRequest(BaseModel):
    """메시지 피드백 요청."""

    message_index: int = Field(..., ge=0)
    rating: Literal["good", "bad"]


class SocratesFeedbackResponse(BaseModel):
    """피드백 저장 결과."""

    success: bool
