"""DiaryOrchestrator 단위 테스트 — cross-domain 흐름 검증."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.orchestrators.diary_orchestrator import DIARY_TEXT_TRUNCATE_CHARS, DiaryOrchestrator

USER_ID_STR = "00000000-0000-0000-0000-000000000001"
DIARY_ID_STR = "00000000-0000-0000-0000-000000000020"


@pytest.fixture
def mock_scrap_service():
    svc = MagicMock()
    scrap_obj = MagicMock()
    scrap_obj.id = UUID("00000000-0000-0000-0000-000000000030")
    svc.create_scrap = AsyncMock(return_value=scrap_obj)
    return svc


@pytest.fixture
def orchestrator(mock_scrap_service):
    return DiaryOrchestrator(mock_scrap_service)


@pytest.mark.asyncio
async def test_process_diary_creates_scrap_then_invokes_librarian(orchestrator, mock_scrap_service):
    """다이어리 → 스크랩 적재 → Librarian 그래프 호출의 흐름."""
    with patch("app.orchestrators.diary_orchestrator.librarian_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={"classification": "wellness"})

        await orchestrator.process_diary_with_librarian(
            diary_id=DIARY_ID_STR,
            content="오늘은 새 프로젝트를 시작했다. 책임감이 크지만 기대된다.",
            user_id=USER_ID_STR,
        )

        # 1) 스크랩으로 적재됐는지
        mock_scrap_service.create_scrap.assert_called_once()
        kwargs = mock_scrap_service.create_scrap.call_args.kwargs
        assert kwargs["user_id"] == UUID(USER_ID_STR)
        assert kwargs["source_type"] == "DIARY"
        assert "다이어리" in kwargs["title"]

        # 2) Librarian 그래프가 호출됐는지
        mock_graph.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_process_diary_swallows_exceptions(orchestrator, mock_scrap_service):
    """백그라운드 task — scrap_service가 예외를 던져도 raise하지 않음 (graceful)."""
    mock_scrap_service.create_scrap.side_effect = RuntimeError("DB unavailable")

    # 예외 raise 안 함 (logger.exception로 처리되고 종료)
    await orchestrator.process_diary_with_librarian(
        diary_id=DIARY_ID_STR,
        content="content" * 100,
        user_id=USER_ID_STR,
    )


@pytest.mark.asyncio
async def test_process_diary_skips_when_scrap_creation_fails(orchestrator, mock_scrap_service):
    """create_scrap이 None을 반환하면 Librarian 호출 자체를 건너뜀."""
    mock_scrap_service.create_scrap.return_value = None

    with patch("app.orchestrators.diary_orchestrator.librarian_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock()

        await orchestrator.process_diary_with_librarian(
            diary_id=DIARY_ID_STR,
            content="content",
            user_id=USER_ID_STR,
        )

        mock_graph.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_process_diary_truncates_long_content(orchestrator, mock_scrap_service):
    """매우 긴 다이어리는 토큰 비용 제어를 위해 자르고 저장."""
    long_content = "긴 내용 " * 5000  # 충분히 큼

    with patch("app.orchestrators.diary_orchestrator.librarian_graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={})

        await orchestrator.process_diary_with_librarian(
            diary_id=DIARY_ID_STR,
            content=long_content,
            user_id=USER_ID_STR,
        )

        # create_scrap에 전달된 content가 잘렸는지
        stored_content = mock_scrap_service.create_scrap.call_args.kwargs["content"]
        assert len(stored_content) == DIARY_TEXT_TRUNCATE_CHARS
