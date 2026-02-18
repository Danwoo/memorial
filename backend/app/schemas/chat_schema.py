from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    """채팅 세션 생성 요청."""

    title: str | None = None


class ChatSessionResponse(BaseModel):
    """채팅 세션 상세 응답."""

    id: UUID
    title: str
    created_at: datetime


class ChatSessionUpdate(BaseModel):
    """채팅 세션 수정 요청."""

    title: str


class ChatMessageRequest(BaseModel):
    """채팅 메시지 전송 요청."""

    content: str
    mode: str | None = None  # insight, counter, summary, evening


class ChatMessageResponse(BaseModel):
    """채팅 이력의 단일 메시지."""

    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


class ChatStreamEvent(BaseModel):
    """채팅 스트리밍 SSE 이벤트."""

    content: str | None = None
    done: bool | None = None
    error: str | None = None


class ChatHistoryResponse(BaseModel):
    """채팅 이력 응답."""

    session_id: UUID
    messages: list[ChatMessageResponse]


class ChatFeedbackRequest(BaseModel):
    """메시지 피드백 요청."""

    message_index: int = Field(..., ge=0)
    rating: Literal["good", "bad"]


class ChatFeedbackResponse(BaseModel):
    """피드백 저장 결과."""

    success: bool
