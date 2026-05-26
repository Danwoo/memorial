import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from supabase import Client

from app.domain.chat import ChatMessageRecord, ChatSession, ChatSessionSummary
from app.utils import parse_iso_datetime

logger = logging.getLogger(__name__)


class ChatRepository:
    """채팅 세션/메시지/피드백 데이터 접근 계층 (Supabase).

    `ChatRepositoryProtocol`을 만족한다 (duck typing).

    Note:
        DB 테이블명은 `socrates_sessions`, `socrates_messages`, `socrates_feedback`로
        historical naming을 유지한다. 운영 데이터 마이그레이션 비용을 피하기 위함이며,
        의미상으로는 모든 agent_type의 채팅 데이터를 다룬다.
    """

    def __init__(self, db: Client):
        self.db = db

    # ------------------------------------------------------------------
    # 세션 — CRUD
    # ------------------------------------------------------------------

    async def create_session(
        self,
        user_id: UUID,
        title: str | None = None,
        agent_type: str = "oracle",
    ) -> ChatSession:
        """새 채팅 세션 생성."""
        resolved_title = title or f"Chat {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
        data = {"user_id": str(user_id), "title": resolved_title, "agent_type": agent_type}

        result = await asyncio.to_thread(self._insert_session, data)

        if result.data:
            return _row_to_session(result.data[0])

        # 폴백 (정상적으로는 도달하지 않음)
        return ChatSession(
            id=uuid4(),
            user_id=user_id,
            title=resolved_title,
            agent_type=agent_type,
            created_at=datetime.now(UTC),
        )

    async def get_session(self, session_id: UUID, user_id: UUID | None = None) -> ChatSession | None:
        """ID로 세션 조회. user_id 지정 시 소유권도 함께 검증."""
        result = await asyncio.to_thread(
            self._select_session, str(session_id), str(user_id) if user_id else None
        )
        if result.data:
            return _row_to_session(result.data[0])
        return None

    async def get_sessions_by_user(
        self,
        user_id: UUID,
        agent_type: str | None = None,
    ) -> list[ChatSession]:
        """사용자의 전체 세션 목록 조회. agent_type 지정 시 필터링."""
        result = await asyncio.to_thread(self._select_sessions_by_user, str(user_id), agent_type)
        return [_row_to_session(s) for s in (result.data or [])]

    async def update_session_title(
        self,
        session_id: UUID,
        title: str,
        user_id: UUID | None = None,
    ) -> bool:
        """세션 제목 업데이트."""
        try:
            await asyncio.to_thread(
                self._update_title, str(session_id), title, str(user_id) if user_id else ""
            )
            return True
        except Exception:
            logger.exception("Error updating session title")
            return False

    async def update_session_summary(self, session_id: UUID, summary: str) -> bool:
        """세션 요약 업데이트."""
        try:
            await asyncio.to_thread(self._update_summary, str(session_id), summary)
            return True
        except Exception:
            logger.exception("세션 요약 업데이트 실패 (session_id=%s)", session_id)
            return False

    async def update_session_topic_tags(self, session_id: UUID, tags: list[str]) -> bool:
        """세션의 topic_tags를 업데이트."""
        try:
            await asyncio.to_thread(self._update_topic_tags, str(session_id), tags)
            return True
        except Exception:
            logger.exception("topic_tags 업데이트 실패 (session_id=%s)", session_id)
            return False

    async def delete_session(self, session_id: UUID, user_id: UUID) -> bool:
        """세션과 소속 메시지 삭제 (user_id 소유권 검증 포함)."""
        try:
            await asyncio.to_thread(self._delete_session, str(session_id), str(user_id))
            return True
        except Exception:
            logger.exception("Error deleting session from Supabase")
            return False

    async def get_recent_session_summaries(
        self,
        user_id: UUID,
        limit: int = 3,
    ) -> list[ChatSessionSummary]:
        """사용자의 최근 세션 요약 조회 (요약이 있는 세션만)."""
        result = await asyncio.to_thread(self._select_recent_summaries, str(user_id), limit)
        return [
            ChatSessionSummary(
                id=UUID(s["id"]),
                title=s["title"],
                summary=s["summary"],
                created_at=parse_iso_datetime(s["created_at"]),
            )
            for s in (result.data or [])
        ]

    async def search_sessions_by_topic(
        self,
        user_id: UUID,
        tags: list[str],
        exclude_session_id: UUID | None = None,
        limit: int = 3,
    ) -> list[ChatSession]:
        """topic_tags 배열과 겹치는 과거 세션 검색."""
        result = await asyncio.to_thread(
            self._select_sessions_by_topic,
            str(user_id),
            tags,
            str(exclude_session_id) if exclude_session_id else None,
            limit,
        )
        return [_row_to_session(s, default_user_id=user_id) for s in (result.data or [])]

    async def get_sessions_for_export(self, user_id: UUID, limit: int = 10000) -> list[ChatSession]:
        """내보내기용 세션 목록 조회."""
        result = await asyncio.to_thread(self._select_sessions_for_export, str(user_id), limit)
        return [_row_to_session(s, default_user_id=user_id) for s in (result.data or [])]

    async def get_sessions_by_date_range(
        self,
        user_id: UUID,
        start_iso: str,
        end_iso: str,
        limit: int = 100,
    ) -> list[ChatSession]:
        """날짜 범위 내 생성된 채팅 세션 목록 조회."""
        result = await asyncio.to_thread(
            self._select_sessions_by_date_range,
            str(user_id),
            start_iso,
            end_iso,
            limit,
        )
        return [_row_to_session(s, default_user_id=user_id) for s in (result.data or [])]

    # ------------------------------------------------------------------
    # 메시지
    # ------------------------------------------------------------------

    async def add_message(self, session_id: UUID, message: BaseMessage) -> bool:
        """세션에 메시지 추가."""
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        content = message.content if hasattr(message, "content") else str(message)

        data = {"session_id": str(session_id), "role": role, "content": content}
        try:
            await asyncio.to_thread(self._insert_message, data)
            return True
        except Exception:
            logger.exception("Error adding message to Supabase")
            return False

    async def get_messages(self, session_id: UUID) -> list[BaseMessage]:
        """세션의 전체 메시지를 LangChain 메시지 형태로 조회."""
        result = await asyncio.to_thread(self._select_messages, str(session_id))
        messages: list[BaseMessage] = []
        if result.data:
            for msg in result.data:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        return messages

    async def get_messages_raw(self, session_id: UUID) -> list[ChatMessageRecord]:
        """세션의 전체 메시지를 타임스탬프 포함 도메인 모델로 조회."""
        result = await asyncio.to_thread(self._select_messages, str(session_id))
        return [
            ChatMessageRecord(
                role=msg["role"],
                content=msg["content"],
                created_at=parse_iso_datetime(msg["created_at"]),
            )
            for msg in (result.data or [])
        ]

    async def get_message_count(self, session_id: UUID) -> int:
        """세션의 메시지 수 조회."""
        result = await asyncio.to_thread(self._count_messages, str(session_id))
        return len(result.data) if result.data else 0

    # ------------------------------------------------------------------
    # 피드백
    # ------------------------------------------------------------------

    async def add_feedback(
        self,
        session_id: UUID,
        message_index: int,
        user_id: UUID,
        rating: str,
    ) -> bool:
        """메시지에 대한 피드백 저장 (upsert)."""
        try:
            await asyncio.to_thread(
                self._upsert_feedback,
                str(session_id),
                message_index,
                str(user_id),
                rating,
            )
            return True
        except Exception:
            logger.exception("피드백 저장 실패")
            return False

    async def get_feedbacks(self, session_id: UUID) -> list[dict]:
        """세션의 전체 피드백 조회 (간단한 매핑이라 dict 그대로)."""
        result = await asyncio.to_thread(self._select_feedbacks, str(session_id))
        return [
            {"message_index": f["message_index"], "rating": f["rating"]}
            for f in (result.data or [])
        ]

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _insert_session(self, data: dict):
        return self.db.table("socrates_sessions").insert(data).execute()

    def _select_session(self, session_id: str, user_id: str | None = None):
        query = self.db.table("socrates_sessions").select("*").eq("id", session_id)
        if user_id:
            query = query.eq("user_id", user_id)
        return query.execute()

    def _select_sessions_by_user(self, user_id: str, agent_type: str | None = None):
        query = self.db.table("socrates_sessions").select("*").eq("user_id", user_id)
        if agent_type:
            query = query.eq("agent_type", agent_type)
        return query.order("created_at", desc=True).execute()

    def _insert_message(self, data: dict):
        return self.db.table("socrates_messages").insert(data).execute()

    def _select_messages(self, session_id: str):
        return (
            self.db.table("socrates_messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

    def _update_title(self, session_id: str, title: str, user_id: str = ""):
        query = (
            self.db.table("socrates_sessions")
            .update({"title": title, "updated_at": datetime.now(UTC).isoformat()})
            .eq("id", session_id)
        )
        if user_id:
            query = query.eq("user_id", user_id)
        return query.execute()

    def _count_messages(self, session_id: str):
        return self.db.table("socrates_messages").select("id").eq("session_id", session_id).execute()

    def _delete_session(self, session_id: str, user_id: str):
        return self.db.table("socrates_sessions").delete().eq("id", session_id).eq("user_id", user_id).execute()

    def _update_summary(self, session_id: str, summary: str):
        return (
            self.db.table("socrates_sessions")
            .update({"summary": summary, "updated_at": datetime.now(UTC).isoformat()})
            .eq("id", session_id)
            .execute()
        )

    def _select_recent_summaries(self, user_id: str, limit: int):
        return (
            self.db.table("socrates_sessions")
            .select("id, title, summary, created_at")
            .eq("user_id", user_id)
            .not_.is_("summary", "null")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _upsert_feedback(self, session_id: str, message_index: int, user_id: str, rating: str):
        return (
            self.db.table("socrates_feedback")
            .upsert(
                {
                    "session_id": session_id,
                    "message_index": message_index,
                    "user_id": user_id,
                    "rating": rating,
                },
                on_conflict="session_id,message_index",
            )
            .execute()
        )

    def _select_sessions_for_export(self, user_id: str, limit: int):
        return (
            self.db.table("socrates_sessions")
            .select("id, title, created_at, agent_type")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _select_sessions_by_date_range(self, user_id: str, start_iso: str, end_iso: str, limit: int = 100):
        return (
            self.db.table("socrates_sessions")
            .select("id, title, created_at, agent_type")
            .eq("user_id", user_id)
            .gte("created_at", start_iso)
            .lte("created_at", end_iso)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    def _update_topic_tags(self, session_id: str, tags: list[str]):
        return (
            self.db.table("socrates_sessions")
            .update({"topic_tags": tags, "updated_at": datetime.now(UTC).isoformat()})
            .eq("id", session_id)
            .execute()
        )

    def _select_sessions_by_topic(self, user_id: str, tags: list[str], exclude_session_id: str | None, limit: int):
        query = (
            self.db.table("socrates_sessions")
            .select("id, title, topic_tags, summary, created_at, agent_type")
            .eq("user_id", user_id)
            .overlaps("topic_tags", tags)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if exclude_session_id:
            query = query.neq("id", exclude_session_id)
        return query.execute()

    def _select_feedbacks(self, session_id: str):
        return (
            self.db.table("socrates_feedback")
            .select("message_index, rating")
            .eq("session_id", session_id)
            .execute()
        )


# ----------------------------------------------------------------------
# Row → 도메인 모델 변환
# ----------------------------------------------------------------------


def _row_to_session(row: dict, default_user_id: UUID | None = None) -> ChatSession:
    """Supabase row를 ChatSession 도메인 모델로 변환.

    Args:
        row: DB row (dict)
        default_user_id: select 결과에 user_id 컬럼이 없는 쿼리(예: by_date_range)일 때 폴백
    """
    raw_user_id = row.get("user_id")
    user_id = UUID(raw_user_id) if raw_user_id else (default_user_id or UUID(int=0))

    return ChatSession(
        id=UUID(row["id"]),
        user_id=user_id,
        title=row["title"],
        agent_type=row.get("agent_type", "oracle"),
        created_at=parse_iso_datetime(row["created_at"]),
        summary=row.get("summary"),
        topic_tags=row.get("topic_tags"),
    )
