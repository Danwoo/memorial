"""
Chat Schemas
Request/Response DTOs for chat endpoints
"""
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ChatSessionCreate(BaseModel):
    """Request to create a new chat session"""
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    """Response with chat session details"""
    id: UUID
    title: str
    created_at: datetime


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""
    content: str
    mode: Optional[str] = None  # insight, counter, summary, evening


class ChatMessageResponse(BaseModel):
    """Single chat message in history"""
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


class ChatStreamEvent(BaseModel):
    """SSE event during chat streaming"""
    content: Optional[str] = None
    done: Optional[bool] = None
    error: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    session_id: UUID
    messages: List[ChatMessageResponse]
