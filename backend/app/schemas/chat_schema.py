"""
Chat Schemas
Request/Response DTOs for chat endpoints
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ChatSessionCreate(BaseModel):
    """Request to create a new chat session"""
    title: str | None = None


class ChatSessionResponse(BaseModel):
    """Response with chat session details"""
    id: UUID
    title: str
    created_at: datetime


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    content: str
    mode: str | None = None  # insight, counter, summary, evening


class ChatMessageResponse(BaseModel):
    """Single chat message in history"""
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


class ChatStreamEvent(BaseModel):
    """SSE event during chat streaming"""
    content: str | None = None
    done: bool | None = None
    error: str | None = None


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    session_id: UUID
    messages: list[ChatMessageResponse]
