"""
Chat Router
API endpoints for chat and Socratic dialogue
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List
from uuid import UUID

from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.services.chat_service import ChatService
from app.dependencies import get_chat_service
from app.config.settings import DEFAULT_USER_ID

router = APIRouter(prefix="/chat", tags=["chat"])

# TODO: Replace with actual user from JWT token
MOCK_USER_ID = DEFAULT_USER_ID


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    data: ChatSessionCreate,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Create a new chat session."""
    session = await chat_service.create_session(MOCK_USER_ID, data.title)
    
    return ChatSessionResponse(
        id=UUID(session["id"]),
        title=session["title"],
        created_at=session["created_at"]
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    chat_service: ChatService = Depends(get_chat_service)
):
    """List all chat sessions for the current user."""
    sessions = await chat_service.list_sessions(MOCK_USER_ID)
    
    return [
        ChatSessionResponse(
            id=UUID(s["id"]),
            title=s["title"],
            created_at=s["created_at"]
        )
        for s in sessions
    ]


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    data: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message and get AI response via SSE streaming."""
    session = await chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return StreamingResponse(
        chat_service.send_message(session_id, MOCK_USER_ID, data.content, data.mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_history(
    session_id: UUID,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get chat history for a session."""
    session = await chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = await chat_service.get_history(session_id)
    
    return [
        ChatMessageResponse(
            role=h["role"],
            content=h["content"],
            created_at=h["created_at"]
        )
        for h in history
    ]
