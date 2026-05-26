from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config.auth import get_user_id
from app.config.dependencies import get_chat_service
from app.domain.chat import ChatMessageRecord, ChatSession
from app.schemas.chat_schema import (
    ChatFeedbackRequest,
    ChatFeedbackResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/socrates", tags=["chat"])


def _session_to_response(session: ChatSession) -> ChatSessionResponse:
    """도메인 모델 → API DTO 변환."""
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        agent_type=session.agent_type,
    )


def _message_to_response(message: ChatMessageRecord) -> ChatMessageResponse:
    """도메인 모델 → API DTO 변환."""
    return ChatMessageResponse(
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    data: ChatSessionCreate,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """새 채팅 세션 생성."""
    session = await chat_service.create_session(user_id, data.title, data.agent_type)
    return _session_to_response(session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """현재 사용자의 채팅 세션 목록 조회."""
    sessions = await chat_service.list_sessions(user_id)
    return [_session_to_response(s) for s in sessions]


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: UUID,
    data: ChatSessionUpdate,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """세션 제목 업데이트."""
    session = await chat_service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await chat_service.update_session_title(session_id, data.title, user_id)
    # 도메인 모델이 frozen이 아니므로 직접 수정 — 또는 model_copy(update=...)
    updated = session.model_copy(update={"title": data.title})
    return _session_to_response(updated)


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    data: ChatMessageRequest,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """메시지 전송 후 SSE 스트리밍으로 AI 응답 반환."""
    session = await chat_service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    source_ctx = data.source_context.model_dump() if data.source_context else None
    return StreamingResponse(
        chat_service.send_message(
            session_id, user_id, data.content, data.mode, source_ctx, data.agent_type
        ),
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
    """특정 세션의 채팅 이력 조회."""
    session = await chat_service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history = await chat_service.get_history(session_id)
    return [_message_to_response(h) for h in history]


@router.post(
    "/sessions/{session_id}/feedback",
    response_model=ChatFeedbackResponse,
)
async def add_feedback(
    session_id: UUID,
    data: ChatFeedbackRequest,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """메시지 피드백 저장 (thumbs up/down)."""
    session = await chat_service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    success = await chat_service.add_feedback(session_id, data.message_index, user_id, data.rating)
    return ChatFeedbackResponse(success=success)


@router.get("/sessions/{session_id}/feedbacks", response_model=list[dict])
async def get_feedbacks(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """세션의 전체 피드백 조회."""
    session = await chat_service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return await chat_service.get_feedbacks(session_id)


@router.post("/sessions/{session_id}/summarize", status_code=200)
async def summarize_session(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    chat_service: ChatService = Depends(get_chat_service),
):
    """세션 대화를 요약하여 저장."""
    session = await chat_service.get_session(session_id, user_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = await chat_service.generate_session_summary(session_id)
    return {"summary": summary}
