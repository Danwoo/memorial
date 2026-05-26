"""ChatRepository 인터페이스 (의존성 역전 원칙).

Service 계층은 이 Protocol을 의존하고, 구체 구현(`ChatRepository`)을 모른다.
테스트에서는 이 Protocol을 만족하는 fake를 주입할 수 있어 격리성이 확보된다.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from langchain_core.messages import BaseMessage

from app.domain.chat import ChatMessageRecord, ChatSession, ChatSessionSummary


@runtime_checkable
class ChatRepositoryProtocol(Protocol):
    """채팅 세션/메시지/피드백 영속화 인터페이스."""

    # ---- 세션 ----
    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
        agent_type: str = "oracle",
    ) -> ChatSession: ...

    async def get_session(
        self,
        session_id: UUID,
        user_id: UUID | None = None,
    ) -> ChatSession | None: ...

    async def get_sessions_by_user(
        self,
        user_id: UUID,
        agent_type: str | None = None,
    ) -> list[ChatSession]: ...

    async def update_session_title(
        self,
        session_id: UUID,
        title: str,
        user_id: UUID | None = None,
    ) -> bool: ...

    async def update_session_summary(self, session_id: UUID, summary: str) -> bool: ...

    async def update_session_topic_tags(self, session_id: UUID, tags: list[str]) -> bool: ...

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool: ...

    async def get_recent_session_summaries(
        self,
        user_id: UUID,
        limit: int = 3,
    ) -> list[ChatSessionSummary]: ...

    async def search_sessions_by_topic(
        self,
        user_id: UUID,
        tags: list[str],
        exclude_session_id: UUID | None = None,
        limit: int = 5,
    ) -> list[ChatSession]: ...

    async def get_sessions_for_export(self, user_id: UUID, limit: int = 10000) -> list[ChatSession]: ...

    async def get_sessions_by_date_range(
        self,
        user_id: UUID,
        start_iso: str,
        end_iso: str,
        limit: int = 100,
    ) -> list[ChatSession]: ...

    # ---- 메시지 ----
    async def add_message(self, session_id: UUID, message: BaseMessage) -> bool: ...

    async def get_messages(self, session_id: UUID) -> list[BaseMessage]: ...

    async def get_messages_raw(self, session_id: UUID) -> list[ChatMessageRecord]: ...

    async def get_message_count(self, session_id: UUID) -> int: ...

    # ---- 피드백 ----
    async def add_feedback(
        self,
        session_id: UUID,
        message_index: int,
        user_id: UUID,
        rating: str,
    ) -> bool: ...

    async def get_feedbacks(self, session_id: UUID) -> list[dict]: ...
