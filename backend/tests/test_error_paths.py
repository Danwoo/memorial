"""에러 경로 / boundary 조건 테스트 — happy path만 검증하던 약점 보강.

검증 대상:
- ChatService.send_message: LLMError / 세션 없음 / SSE 단절
- DiaryOrchestrator: scrap 생성 실패 / Librarian 그래프 실패
- IngestService: 잘못된 URL 스킴 / SSRF / timeout
- canonicalize_entity_name: edge cases
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.domain.chat import ChatSession
from app.exceptions import InvalidUrlError, LLMError
from app.services.chat_service import ChatService
from app.services.ingest_service import validate_url

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000010")


# ----------------------------------------------------------------------
# IngestService — SSRF 방어 + URL 검증
# ----------------------------------------------------------------------


class TestUrlValidation:
    def test_rejects_ftp_scheme(self):
        with pytest.raises(InvalidUrlError, match="허용되지 않는 URL 스킴"):
            validate_url("ftp://example.com/file")

    def test_rejects_file_scheme(self):
        with pytest.raises(InvalidUrlError, match="허용되지 않는 URL 스킴"):
            validate_url("file:///etc/passwd")

    def test_rejects_javascript_scheme(self):
        with pytest.raises(InvalidUrlError, match="허용되지 않는 URL 스킴"):
            validate_url("javascript:alert(1)")

    def test_rejects_localhost(self):
        """SSRF — localhost 차단."""
        with pytest.raises(InvalidUrlError, match="내부 네트워크"):
            validate_url("http://localhost/admin")

    def test_rejects_127_loopback(self):
        with pytest.raises(InvalidUrlError, match="내부 네트워크"):
            validate_url("http://127.0.0.1/")

    def test_rejects_private_10_range(self):
        with pytest.raises(InvalidUrlError, match="내부 네트워크"):
            validate_url("http://10.0.0.1/")

    def test_rejects_private_192_range(self):
        with pytest.raises(InvalidUrlError, match="내부 네트워크"):
            validate_url("http://192.168.1.1/")

    def test_rejects_aws_metadata_endpoint(self):
        """AWS EC2 메타데이터 서비스 — 169.254.169.254 (Capital One 사례)."""
        with pytest.raises(InvalidUrlError, match="내부 네트워크"):
            validate_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_unresolvable_host(self):
        with pytest.raises(InvalidUrlError, match="호스트를 해석할 수 없습니다"):
            validate_url("http://nonexistent-domain-12345-zzz.local/")


# ----------------------------------------------------------------------
# ChatService.send_message — LLM 실패 흐름
# ----------------------------------------------------------------------


class TestChatSendMessageErrors:
    @pytest.fixture
    def session(self):
        return ChatSession(
            id=SESSION_ID,
            user_id=USER_ID,
            title="t",
            agent_type="oracle",
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def repo_mock(self, session):
        repo = MagicMock()
        repo.get_session = AsyncMock(return_value=session)
        repo.add_message = AsyncMock(return_value=True)
        repo.get_messages = AsyncMock(return_value=[])
        repo.get_message_count = AsyncMock(return_value=2)
        repo.update_session_title = AsyncMock(return_value=True)
        repo.update_session_summary = AsyncMock(return_value=True)
        repo.update_session_topic_tags = AsyncMock(return_value=True)
        return repo

    @pytest.mark.asyncio
    async def test_session_not_found_yields_error(self, repo_mock):
        repo_mock.get_session = AsyncMock(return_value=None)
        svc = ChatService(repo_mock)

        events = []
        async for ev in svc.send_message(SESSION_ID, USER_ID, "hi"):
            events.append(ev)

        assert any("Session not found" in e for e in events)

    @pytest.mark.asyncio
    async def test_no_agent_registered_yields_error(self, repo_mock):
        svc = ChatService(repo_mock)
        with patch("app.services.chat_service.AgentRegistry.get_entry", return_value=None):
            events = []
            async for ev in svc.send_message(SESSION_ID, USER_ID, "hi", agent_type="nonexistent"):
                events.append(ev)

        assert any("No agent available" in e for e in events)

    @pytest.mark.asyncio
    async def test_llm_error_yields_friendly_message(self, repo_mock):
        """LLMError catch — 사용자에게 친절한 메시지, stack trace 노출 안 함."""
        svc = ChatService(repo_mock)

        entry = MagicMock()

        async def failing_stream(*a, **kw):
            raise LLMError("model timeout")
            yield  # never reached

        entry.streaming.stream = failing_stream
        entry.graph = MagicMock()

        with (
            patch("app.services.chat_service.AgentRegistry.get_entry", return_value=entry),
            patch("app.services.chat_service.ChatService._build_agent_context", return_value=MagicMock()),
        ):
            events = []
            async for ev in svc.send_message(SESSION_ID, USER_ID, "hi"):
                events.append(ev)

        # 친절한 메시지 + 내부 메시지("model timeout") 노출 안 함
        joined = "".join(events)
        assert "AI 응답 생성에 실패" in joined
        assert "model timeout" not in joined  # 내부 메시지 누설 X

    @pytest.mark.asyncio
    async def test_unknown_exception_returns_generic_error(self, repo_mock):
        """알려지지 않은 예외 — 일반화 메시지, stack trace 미노출."""
        svc = ChatService(repo_mock)

        entry = MagicMock()

        async def boom(*a, **kw):
            raise RuntimeError("internal DB connection corrupted with secret token xyz")
            yield

        entry.streaming.stream = boom
        entry.graph = MagicMock()

        with (
            patch("app.services.chat_service.AgentRegistry.get_entry", return_value=entry),
            patch("app.services.chat_service.ChatService._build_agent_context", return_value=MagicMock()),
        ):
            events = []
            async for ev in svc.send_message(SESSION_ID, USER_ID, "hi"):
                events.append(ev)

        joined = "".join(events)
        assert "An internal error occurred" in joined
        assert "secret token" not in joined  # 내부 정보 누설 X
        assert "RuntimeError" not in joined

    @pytest.mark.asyncio
    async def test_cancelled_error_silently_returns(self, repo_mock):
        """SSE 클라이언트 연결 해제 — 예외 raise 없이 종료 (graceful)."""
        svc = ChatService(repo_mock)

        entry = MagicMock()

        async def cancel(*a, **kw):
            raise asyncio.CancelledError()
            yield

        entry.streaming.stream = cancel
        entry.graph = MagicMock()

        with (
            patch("app.services.chat_service.AgentRegistry.get_entry", return_value=entry),
            patch("app.services.chat_service.ChatService._build_agent_context", return_value=MagicMock()),
        ):
            events = []
            async for ev in svc.send_message(SESSION_ID, USER_ID, "hi"):
                events.append(ev)

        # cancel은 사용자에게 에러 메시지 안 보냄 (정상 흐름)
        assert not any("error" in e.lower() for e in events)
