"""
Chat API Endpoints
Based on API_Spec.md - Section 4

Handles:
- POST /chat/sessions - Create new chat session
- POST /chat/sessions/{id}/messages - Send message (SSE streaming)
- GET /chat/sessions - List sessions
- GET /chat/sessions/{id}/history - Get chat history
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import json

from langchain_core.messages import HumanMessage, AIMessage
from app.agents.socrates import socrates_graph
from app.agents.state import AgentState
from app.core.supabase import get_supabase
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from supabase import Client

router = APIRouter(prefix="/chat", tags=["chat"])

# TODO: Replace with actual user from JWT token  
MOCK_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


# ========================================
# In-memory session store (for MVP)
# TODO: Replace with Supabase persistence
# ========================================
chat_sessions: dict[str, dict] = {}


# ========================================
# Endpoints
# ========================================
@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    data: ChatSessionCreate,
    db: Client = Depends(get_supabase)
):
    """
    Create a new chat session.
    """
    session_id = uuid4()
    title = data.title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    session = {
        "id": str(session_id),
        "user_id": str(MOCK_USER_ID),
        "title": title,
        "messages": [],
        "created_at": datetime.now()
    }
    
    chat_sessions[str(session_id)] = session
    
    return ChatSessionResponse(
        id=session_id,
        title=title,
        created_at=session["created_at"]
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions():
    """
    List all chat sessions for the current user.
    """
    user_sessions = [
        ChatSessionResponse(
            id=UUID(s["id"]),
            title=s["title"],
            created_at=s["created_at"]
        )
        for s in chat_sessions.values()
        if s["user_id"] == str(MOCK_USER_ID)
    ]
    return sorted(user_sessions, key=lambda x: x.created_at, reverse=True)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    data: ChatMessageRequest
):
    """
    Send a message and get AI response via SSE streaming.
    
    Response is Server-Sent Events format for real-time streaming.
    """
    session_key = str(session_id)
    
    if session_key not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_key]
    
    # Add user message to history
    user_msg = HumanMessage(content=data.content)
    session["messages"].append(user_msg)
    
    async def generate_sse() -> AsyncGenerator[str, None]:
        """Generate SSE stream"""
        try:
            # Build initial state with mode
            initial_state: AgentState = {
                "messages": session["messages"],
                "user_id": str(MOCK_USER_ID),
                "context": {"mode": data.mode} if data.mode else {},
                "target_memory_id": None,
                "target_text": None,
                "classification": None,
                "summary": None,
                "tags": None,
                "extracted_entities": None,
                "extracted_relations": None,
                "is_streaming": True,
                "next_step": None,
                "error": None
            }
            
            # Run Socrates graph
            result = await socrates_graph.ainvoke(initial_state)
            
            # Get AI response
            new_messages = result.get("messages", [])
            if new_messages:
                ai_msg = new_messages[-1]
                content = ai_msg.content if hasattr(ai_msg, 'content') else str(ai_msg)
                
                # Add to session history
                session["messages"].append(AIMessage(content=content))
                
                # Stream the response in chunks
                chunk_size = 50
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            
            # Send done signal
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/sessions/{session_id}/history", response_model=List[ChatMessageResponse])
async def get_history(session_id: UUID):
    """
    Get chat history for a session.
    """
    session_key = str(session_id)
    
    if session_key not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = chat_sessions[session_key]
    messages = session.get("messages", [])
    
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append(ChatMessageResponse(
                role="user",
                content=msg.content,
                created_at=datetime.now()  # TODO: Store actual timestamps
            ))
        elif isinstance(msg, AIMessage):
            result.append(ChatMessageResponse(
                role="assistant",
                content=msg.content,
                created_at=datetime.now()
            ))
    
    return result
