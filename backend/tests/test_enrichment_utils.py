"""enrichment_utils 공유 유틸리티 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestFormatMemoriesWithBudget:
    """format_memories_with_budget 함수 테스트."""

    def test_empty_memories_returns_empty(self):
        """빈 목록 → 빈 문자열."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        assert format_memories_with_budget([]) == ""

    def test_single_memory_formatted(self):
        """단일 메모리 — 헤더+내용 포함."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        memories = [{"id": "1", "title": "테스트", "content": "내용입니다", "created_at": "2026-01-01T00:00:00"}]
        result = format_memories_with_budget(memories)

        assert "테스트" in result
        assert "내용입니다" in result
        assert "[2026-01-01]" in result

    def test_budget_limits_content(self):
        """budget 제한 시 내용 잘림."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        long_content = "A" * 5000
        memories = [{"id": "1", "title": "제목", "content": long_content, "created_at": "2026-01-01"}]
        result = format_memories_with_budget(memories, budget=200)

        assert len(result) < 5100  # 원본보다 훨씬 짧음

    def test_include_url_shows_source(self):
        """include_url=True 시 출처 URL 표시."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        memories = [
            {
                "id": "1",
                "title": "스크랩",
                "content": "내용",
                "source_url": "https://example.com",
                "created_at": "2026-01-01",
            }
        ]
        result = format_memories_with_budget(memories, include_url=True)

        assert "https://example.com" in result

    def test_multiple_memories_ranked_by_rrf(self):
        """여러 메모리 — 상위 결과에 더 많은 예산 할당."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        memories = [
            {"id": str(i), "title": f"메모리 {i}", "content": "X" * 1000, "created_at": "2026-01-01"} for i in range(3)
        ]
        result = format_memories_with_budget(memories, budget=1000)

        # 모든 메모리가 결과에 포함되어야 함
        assert "메모리 0" in result
        assert "메모리 1" in result
        assert "메모리 2" in result

    def test_custom_item_label(self):
        """item_label 파라미터 반영."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        memories = [{"id": "1", "title": "항목", "content": "내용", "created_at": "2026-01-01"}]
        result = format_memories_with_budget(memories, item_label="스크랩")

        assert "스크랩 #1" in result

    def test_summary_preferred_over_content(self):
        """summary가 있으면 content 대신 summary 사용."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        memories = [
            {
                "id": "1",
                "title": "항목",
                "summary": "요약본",
                "content": "원본 내용",
                "created_at": "2026-01-01",
            }
        ]
        result = format_memories_with_budget(memories)

        assert "요약본" in result
        assert "원본 내용" not in result


class TestFormatMemoriesWithBudgetTags:
    """태그 표시 테스트."""

    def test_tags_shown_in_header(self):
        """태그가 있으면 헤더에 표시."""
        from app.agents.shared.enrichment_utils import format_memories_with_budget

        memories = [
            {
                "id": "1",
                "title": "태그 테스트",
                "content": "내용",
                "tags": ["Python", "함수형"],
                "created_at": "2026-01-01",
            }
        ]
        result = format_memories_with_budget(memories)

        assert "Python" in result
        assert "함수형" in result


class TestFindContradictingItems:
    """find_contradicting_items 함수 테스트."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_results(self):
        """검색 결과 없으면 빈 리스트 반환."""
        from app.agents.shared.enrichment_utils import find_contradicting_items

        mock_vector_repo = MagicMock()
        mock_vector_repo.similarity_search = AsyncMock(return_value=[])

        result = await find_contradicting_items(
            query="테스트",
            current_items=[],
            user_id="user-1",
            vector_repo=mock_vector_repo,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_excludes_already_referenced_items(self):
        """current_items에 있는 ID는 결과에서 제외."""
        from app.agents.shared.enrichment_utils import find_contradicting_items

        existing = {"id": "existing-1", "title": "기존", "content": "내용"}
        mock_vector_repo = MagicMock()
        mock_vector_repo.similarity_search = AsyncMock(return_value=[existing])

        result = await find_contradicting_items(
            query="테스트",
            current_items=[existing],
            user_id="user-1",
            vector_repo=mock_vector_repo,
        )

        assert result == []


class TestBuildContradictionContext:
    """build_contradiction_context 함수 테스트."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_contradictions(self):
        """반론 없으면 빈 문자열 반환."""
        from app.agents.shared.enrichment_utils import build_contradiction_context

        mock_vector_repo = MagicMock()
        mock_vector_repo.similarity_search = AsyncMock(return_value=[])

        result = await build_contradiction_context(
            query="테스트",
            current_items=[],
            user_id="user-1",
            vector_repo=mock_vector_repo,
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_formats_contradiction_items(self):
        """반론 항목 포맷 확인."""
        from app.agents.shared.enrichment_utils import build_contradiction_context

        contradiction = {
            "id": "contra-1",
            "title": "반론 제목",
            "content": "반론 내용",
            "created_at": "2026-01-15T00:00:00",
        }
        mock_vector_repo = MagicMock()
        mock_vector_repo.similarity_search = AsyncMock(return_value=[contradiction])

        result = await build_contradiction_context(
            query="테스트",
            current_items=[],
            user_id="user-1",
            vector_repo=mock_vector_repo,
        )

        assert "반론 제목" in result
        assert "2026-01-15" in result
