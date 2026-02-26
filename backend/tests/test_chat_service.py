from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.services.socrates_service import SocratesService

NOW = datetime.now(UTC)
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
SESSION_ID_1 = UUID("00000000-0000-0000-0000-000000000010")
SESSION_ID_2 = UUID("00000000-0000-0000-0000-000000000020")


class TestSocratesService:
    """SocratesService 단위 테스트 — 세션 생성, 메시지 저장, 세션 목록 정렬, 피드백"""

    @pytest.fixture
    def mock_chat_repo(self):
        """ChatRepository 목 생성"""
        repo = MagicMock()
        repo.create_session = AsyncMock()
        repo.get_session = AsyncMock()
        repo.get_sessions_by_user = AsyncMock()
        repo.add_message = AsyncMock()
        repo.get_messages = AsyncMock()
        repo.get_messages_raw = AsyncMock()
        repo.get_message_count = AsyncMock()
        repo.update_session_title = AsyncMock()
        repo.update_session_summary = AsyncMock()
        repo.add_feedback = AsyncMock()
        repo.get_feedbacks = AsyncMock()
        repo.get_recent_session_summaries = AsyncMock()
        return repo

    @pytest.fixture
    def chat_service(self, mock_chat_repo):
        """목 의존성 주입된 SocratesService 생성"""
        return SocratesService(mock_chat_repo)

    # --- 세션 생성 테스트 ---

    @pytest.mark.asyncio
    async def test_create_session_default_title(self, chat_service, mock_chat_repo):
        """기본 제목 없이 세션 생성이 정상 동작하는지 확인"""
        expected = {"id": str(SESSION_ID_1), "user_id": str(USER_ID), "title": None, "created_at": NOW.isoformat()}
        mock_chat_repo.create_session.return_value = expected

        result = await chat_service.create_session(USER_ID)

        assert result["id"] == str(SESSION_ID_1)
        mock_chat_repo.create_session.assert_called_once_with(USER_ID, None)

    @pytest.mark.asyncio
    async def test_create_session_with_title(self, chat_service, mock_chat_repo):
        """사용자 지정 제목으로 세션 생성"""
        expected = {
            "id": str(SESSION_ID_1),
            "user_id": str(USER_ID),
            "title": "오늘의 회고",
            "created_at": NOW.isoformat(),
        }
        mock_chat_repo.create_session.return_value = expected

        result = await chat_service.create_session(USER_ID, title="오늘의 회고")

        assert result["title"] == "오늘의 회고"
        mock_chat_repo.create_session.assert_called_once_with(USER_ID, "오늘의 회고")

    # --- 세션 조회 테스트 ---

    @pytest.mark.asyncio
    async def test_get_session_found(self, chat_service, mock_chat_repo):
        """존재하는 세션 ID로 조회 시 정상 반환"""
        expected = {"id": str(SESSION_ID_1), "title": "테스트 세션"}
        mock_chat_repo.get_session.return_value = expected

        result = await chat_service.get_session(SESSION_ID_1)

        assert result is not None
        assert result["id"] == str(SESSION_ID_1)

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, chat_service, mock_chat_repo):
        """존재하지 않는 세션 ID로 조회 시 None 반환"""
        mock_chat_repo.get_session.return_value = None

        result = await chat_service.get_session(SESSION_ID_1)

        assert result is None

    # --- 세션 목록 정렬 테스트 ---

    @pytest.mark.asyncio
    async def test_list_sessions_sorted_by_latest(self, chat_service, mock_chat_repo):
        """세션 목록이 최신순(created_at 내림차순)으로 정렬되는지 확인"""
        older = NOW - timedelta(days=2)
        newer = NOW

        mock_chat_repo.get_sessions_by_user.return_value = [
            {"id": str(SESSION_ID_1), "title": "오래된 세션", "created_at": older},
            {"id": str(SESSION_ID_2), "title": "최근 세션", "created_at": newer},
        ]

        result = await chat_service.list_sessions(USER_ID)

        # Assert — 최신 세션이 먼저
        assert result[0]["id"] == str(SESSION_ID_2)
        assert result[1]["id"] == str(SESSION_ID_1)

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, chat_service, mock_chat_repo):
        """세션이 없는 사용자의 목록 조회 시 빈 리스트 반환"""
        mock_chat_repo.get_sessions_by_user.return_value = []

        result = await chat_service.list_sessions(USER_ID)

        assert result == []

    # --- 채팅 이력 조회 테스트 ---

    @pytest.mark.asyncio
    async def test_get_history(self, chat_service, mock_chat_repo):
        """세션의 채팅 이력이 raw 메시지 형태로 반환되는지 확인"""
        expected_messages = [
            {"role": "user", "content": "안녕하세요", "created_at": NOW.isoformat()},
            {"role": "assistant", "content": "반갑습니다!", "created_at": NOW.isoformat()},
        ]
        mock_chat_repo.get_messages_raw.return_value = expected_messages

        result = await chat_service.get_history(SESSION_ID_1)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        mock_chat_repo.get_messages_raw.assert_called_once_with(SESSION_ID_1)

    # --- 피드백 저장/조회 테스트 ---

    @pytest.mark.asyncio
    async def test_add_feedback_success(self, chat_service, mock_chat_repo):
        """메시지 피드백(좋아요/싫어요) 저장 성공"""
        mock_chat_repo.add_feedback.return_value = True

        result = await chat_service.add_feedback(SESSION_ID_1, message_index=1, user_id=USER_ID, rating="like")

        assert result is True
        mock_chat_repo.add_feedback.assert_called_once_with(SESSION_ID_1, 1, USER_ID, "like")

    @pytest.mark.asyncio
    async def test_get_feedbacks(self, chat_service, mock_chat_repo):
        """세션의 전체 피드백 목록 조회"""
        expected = [
            {"message_index": 1, "rating": "like"},
            {"message_index": 3, "rating": "dislike"},
        ]
        mock_chat_repo.get_feedbacks.return_value = expected

        result = await chat_service.get_feedbacks(SESSION_ID_1)

        assert len(result) == 2
        assert result[0]["rating"] == "like"

    # --- 세션 제목 업데이트 테스트 ---

    @pytest.mark.asyncio
    async def test_update_session_title(self, chat_service, mock_chat_repo):
        """세션 제목 수동 업데이트 성공"""
        mock_chat_repo.update_session_title.return_value = True

        result = await chat_service.update_session_title(SESSION_ID_1, "새 제목")

        assert result is True
        mock_chat_repo.update_session_title.assert_called_once_with(SESSION_ID_1, "새 제목")
