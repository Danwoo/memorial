"""채팅 도메인 모델 (Pydantic).

DB row(`dict`)나 API DTO(`app/schemas/chat_schema.py`)와 구분되는 비즈니스 엔티티.
- Repository는 DB row → ChatSession/ChatMessageRecord 변환을 책임진다.
- Service는 도메인 모델을 받아 비즈니스 로직을 수행한다.
- Router는 도메인 모델 → DTO(`ChatSessionResponse` 등)로 변환하여 응답한다.

이 분리로 mypy strict 통과 + 비즈니스 불변식을 모델 레벨에서 보장한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSession(BaseModel):
    """채팅 세션 도메인 엔티티."""

    model_config = ConfigDict(frozen=False)

    id: UUID
    user_id: UUID
    title: str
    agent_type: str = "oracle"
    created_at: datetime
    summary: str | None = None
    topic_tags: list[str] | None = None


class ChatMessageRecord(BaseModel):
    """DB에서 읽은 채팅 메시지 (created_at 포함, raw 형태)."""

    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ChatFeedback(BaseModel):
    """채팅 피드백 엔티티."""

    model_config = ConfigDict(frozen=True)

    message_index: int = Field(..., ge=0)
    rating: Literal["like", "dislike", "good", "bad"]


class ChatSessionSummary(BaseModel):
    """세션 요약 (이전 대화 컨텍스트 조회용)."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    summary: str
    created_at: datetime
