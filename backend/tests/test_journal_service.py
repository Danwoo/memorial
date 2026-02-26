from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.services.diary_service import DiaryService

NOW = datetime.now(UTC)
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
JOURNAL_ID = UUID("00000000-0000-0000-0000-000000000010")
MEM_ID_1 = "00000000-0000-0000-0000-000000000020"
MEM_ID_2 = "00000000-0000-0000-0000-000000000030"


class TestDiaryService:
    """DiaryService 단위 테스트 — 다이어리 생성/업데이트, 날짜별 조회, 스크랩 링크"""

    @pytest.fixture
    def mock_journal_repo(self):
        """JournalRepository 목 생성"""
        repo = MagicMock()
        repo.create_diary = AsyncMock()
        repo.get_diaries = AsyncMock()
        repo.get_diary_dates = AsyncMock()
        repo.get_diaries_by_date = AsyncMock()
        return repo

    @pytest.fixture
    def mock_graph_repo(self):
        """GraphRepository 목 생성"""
        repo = MagicMock()
        repo.is_connected = True
        return repo

    @pytest.fixture
    def mock_vector_repo(self):
        """VectorRepository 목 생성"""
        repo = MagicMock()
        repo.similarity_search = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_link_repo(self):
        """JournalMemoryLinkRepository 목 생성"""
        repo = MagicMock()
        repo.sync_links = AsyncMock()
        return repo

    @pytest.fixture
    def journal_service(self, mock_journal_repo, mock_graph_repo, mock_vector_repo, mock_link_repo):
        """목 의존성 주입된 JournalService 생성"""
        return DiaryService(
            mock_journal_repo,
            mock_graph_repo,
            vector_repo=mock_vector_repo,
            link_repo=mock_link_repo,
        )

    # --- 저널 생성 테스트 ---

    @pytest.mark.asyncio
    async def test_create_entry_success(self, journal_service, mock_journal_repo):
        """저널 생성 시 감정 분석 포함하여 저장되는지 확인"""
        expected = {
            "id": str(JOURNAL_ID),
            "content": "오늘 좋은 하루",
            "mood": "NEUTRAL",
            "created_at": NOW.isoformat(),
        }
        mock_journal_repo.create_diary.return_value = expected

        result = await journal_service.create_entry(USER_ID, "오늘 좋은 하루")

        assert result is not None
        assert result["id"] == str(JOURNAL_ID)
        mock_journal_repo.create_diary.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_entry_with_memory_links(self, journal_service, mock_journal_repo, mock_link_repo):
        """저널 생성 시 memory_ids가 있으면 링크 동기화가 호출되는지 확인"""
        expected = {"id": str(JOURNAL_ID), "content": "학습 기록", "mood": "NEUTRAL", "created_at": NOW.isoformat()}
        mock_journal_repo.create_diary.return_value = expected

        await journal_service.create_entry(USER_ID, "학습 기록", scrap_ids=[MEM_ID_1, MEM_ID_2])

        mock_link_repo.sync_links.assert_called_once_with(JOURNAL_ID, [MEM_ID_1, MEM_ID_2], link_type="manual")

    @pytest.mark.asyncio
    async def test_create_entry_without_memory_links(self, journal_service, mock_journal_repo, mock_link_repo):
        """memory_ids가 없으면 링크 동기화가 호출되지 않는지 확인"""
        expected = {"id": str(JOURNAL_ID), "content": "일반 일기", "mood": "NEUTRAL", "created_at": NOW.isoformat()}
        mock_journal_repo.create_diary.return_value = expected

        await journal_service.create_entry(USER_ID, "일반 일기")

        mock_link_repo.sync_links.assert_not_called()

    # --- 저널 목록 조회 테스트 ---

    @pytest.mark.asyncio
    async def test_get_entries(self, journal_service, mock_journal_repo):
        """사용자의 저널 목록 조회가 정상 동작하는지 확인"""
        expected = [
            {"id": str(JOURNAL_ID), "content": "첫 번째 저널", "created_at": NOW.isoformat()},
        ]
        mock_journal_repo.get_diaries.return_value = expected

        result = await journal_service.get_entries(USER_ID, limit=10)

        assert len(result) == 1
        mock_journal_repo.get_diaries.assert_called_once_with(USER_ID, 10)

    # --- 날짜별 조회 테스트 ---

    @pytest.mark.asyncio
    async def test_get_journal_dates_aggregation(self, journal_service, mock_journal_repo):
        """같은 날짜의 저널이 count 기준으로 집계되는지 확인"""
        mock_journal_repo.get_diary_dates.return_value = [
            {"created_at": "2026-02-20T10:00:00", "mood": "POSITIVE"},
            {"created_at": "2026-02-20T18:00:00", "mood": "NEUTRAL"},
            {"created_at": "2026-02-19T12:00:00", "mood": "NEGATIVE"},
        ]

        result = await journal_service.get_diary_dates(USER_ID)

        # Assert — 2/20은 count=2, 2/19는 count=1, 최신순 정렬
        assert result[0]["date"] == "2026-02-20"
        assert result[0]["count"] == 2
        assert result[1]["date"] == "2026-02-19"
        assert result[1]["count"] == 1

    @pytest.mark.asyncio
    async def test_get_journals_by_date(self, journal_service, mock_journal_repo):
        """특정 날짜의 저널 목록이 정상 반환되는지 확인"""
        expected = [
            {"id": str(JOURNAL_ID), "content": "오전 저널", "created_at": "2026-02-20T10:00:00"},
        ]
        mock_journal_repo.get_diaries_by_date.return_value = expected

        result = await journal_service.get_diaries_by_date(USER_ID, "2026-02-20")

        assert len(result) == 1
        mock_journal_repo.get_diaries_by_date.assert_called_once_with(USER_ID, "2026-02-20")

    # --- 인지 왜곡 탐지 테스트 ---

    def test_detect_cognitive_distortions_found(self, journal_service):
        """인지 왜곡 키워드가 포함된 텍스트에서 탐지가 동작하는지 확인"""
        content = "나는 항상 실패한다. 내 탓이야. 모든 것이 끔찍하다."

        result = journal_service.detect_cognitive_distortions(content)

        assert result["has_distortions"] is True
        assert len(result["distortions"]) >= 2
        assert result["wellness_score"] < 100

        # 탐지된 패턴 타입 확인
        detected_types = {d["type"] for d in result["distortions"]}
        assert "all_or_nothing" in detected_types
        assert "personalization" in detected_types

    def test_detect_cognitive_distortions_none(self, journal_service):
        """인지 왜곡이 없는 텍스트에서 빈 결과 반환"""
        content = "공원에서 산책을 하며 좋은 시간을 보냈다."

        result = journal_service.detect_cognitive_distortions(content)

        assert result["has_distortions"] is False
        assert result["distortions"] == []
        assert result["wellness_score"] == 100

    # --- 관련 메모리 검색 테스트 ---

    @pytest.mark.asyncio
    async def test_get_related_memories(self, journal_service, mock_vector_repo):
        """저널 내용 기반 관련 메모리 검색이 정상 동작하는지 확인"""
        mock_vector_repo.similarity_search.return_value = [
            {
                "id": MEM_ID_1,
                "title": "파이썬 학습",
                "summary": "파이썬 기초",
                "type": "memory",
                "created_at": NOW.isoformat(),
                "similarity": 0.8,
            },
        ]

        result = await journal_service.get_related_scraps(USER_ID, "파이썬 공부를 시작했다")

        assert len(result) == 1
        assert result[0]["title"] == "파이썬 학습"
        mock_vector_repo.similarity_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_related_memories_short_content(self, journal_service, mock_vector_repo):
        """내용이 너무 짧으면 검색을 건너뛰고 빈 리스트 반환"""
        result = await journal_service.get_related_scraps(USER_ID, "짧")

        assert result == []
        mock_vector_repo.similarity_search.assert_not_called()
