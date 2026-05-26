"""통합 테스트 공용 fixture.

전략:
- FastAPI app은 그대로 import하되, lifespan은 호출하지 않는다 (KuzuDB rebuild,
  스케줄러 등 외부 의존성 시작을 회피).
- 인증/repository/service는 dependency_overrides로 fake 주입.
- 테스트는 router 레벨에서 요청 → 응답 contract을 검증한다.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

# Lifespan 호출 전에 환경변수 세팅 — Settings가 lru_cache라 import 순서 중요
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("KUZU_DB_PATH", "")  # KuzuDB 비활성화


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000010")
DIARY_ID = UUID("00000000-0000-0000-0000-000000000020")


@pytest.fixture
def client():
    """lifespan 없이 TestClient — 외부 의존성(KuzuDB rebuild) 회피."""
    from app.config.auth import get_user_id
    from app.main import app

    # 인증 우회 — 모든 테스트가 USER_ID로 호출됨
    app.dependency_overrides[get_user_id] = lambda: USER_ID

    with TestClient(app) as c:
        # TestClient context manager가 lifespan을 호출하지만,
        # KUZU_DB_PATH가 비어있어 rebuild가 즉시 0 반환 → 비용 무시
        yield c

    app.dependency_overrides.clear()


def make_chat_service_mock():
    """ChatService AsyncMock — 메서드별 기본값 세팅."""
    from app.domain.chat import ChatMessageRecord, ChatSession

    now = datetime.now(UTC)
    sample = ChatSession(
        id=SESSION_ID,
        user_id=USER_ID,
        title="Test Session",
        agent_type="oracle",
        created_at=now,
    )

    svc = MagicMock()
    svc.create_session = AsyncMock(return_value=sample)
    svc.get_session = AsyncMock(return_value=sample)
    svc.list_sessions = AsyncMock(return_value=[sample])
    svc.update_session_title = AsyncMock(return_value=True)
    svc.get_history = AsyncMock(
        return_value=[
            ChatMessageRecord(role="user", content="안녕", created_at=now),
            ChatMessageRecord(role="assistant", content="네", created_at=now),
        ]
    )
    svc.add_feedback = AsyncMock(return_value=True)
    svc.get_feedbacks = AsyncMock(return_value=[])
    svc.generate_session_summary = AsyncMock(return_value="요약")
    return svc


def make_diary_service_mock():
    """DiaryService AsyncMock."""
    from app.domain.diary import DiaryEntry

    now = datetime.now(UTC)
    sample = DiaryEntry(
        id=DIARY_ID,
        user_id=USER_ID,
        content="오늘의 일기",
        mood="POSITIVE",
        tags=["test"],
        created_at=now,
    )

    svc = MagicMock()
    svc.create_entry = AsyncMock(return_value=sample)
    svc.get_entries = AsyncMock(return_value=[sample])
    svc.update_entry = AsyncMock(return_value=sample)
    svc.get_diary_dates = AsyncMock(return_value=[{"date": "2026-05-26", "count": 1, "mood": "POSITIVE", "tags": []}])
    svc.get_diaries_by_date = AsyncMock(return_value=[sample])
    return svc
