"""
Chat Router
API endpoints for chat and Socratic dialogue
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)
from app.security.auth import get_user_id
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    data: ChatSessionCreate,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Create a new chat session."""
    session = await chat_service.create_session(user_id, data.title)

    return ChatSessionResponse(
        id=UUID(session["id"]),
        title=session["title"],
        created_at=session["created_at"],
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """List all chat sessions for the current user."""
    sessions = await chat_service.list_sessions(user_id)

    return [
        ChatSessionResponse(
            id=UUID(s["id"]),
            title=s["title"],
            created_at=s["created_at"],
        )
        for s in sessions
    ]


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    data: ChatMessageRequest,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Send a message and get AI response via SSE streaming."""
    session = await chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return StreamingResponse(
        chat_service.send_message(session_id, user_id, data.content, data.mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/sessions/{session_id}/history",
    response_model=list[ChatMessageResponse],
)
async def get_history(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get chat history for a session."""
    session = await chat_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("user_id") != str(user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    history = await chat_service.get_history(session_id)

    return [
        ChatMessageResponse(
            role=h["role"],
            content=h["content"],
            created_at=h["created_at"],
        )
        for h in history
    ]
