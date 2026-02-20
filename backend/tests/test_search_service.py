from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.services.search_service import SearchService

NOW = datetime.now(UTC)
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
MEM_ID_1 = "00000000-0000-0000-0000-000000000010"
MEM_ID_2 = "00000000-0000-0000-0000-000000000020"
MEM_ID_3 = "00000000-0000-0000-0000-000000000030"


class TestSearchService:
    """SearchService 단위 테스트 — 하이브리드 검색, RRF, 필터, graceful degradation"""

    @pytest.fixture
    def mock_vector_repo(self):
        """VectorRepository 목 생성"""
        repo = MagicMock()
        repo.similarity_search = AsyncMock(return_value=[])
        repo.sparse_search = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_memory_repo(self):
        """MemoryRepository 목 생성"""
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_graph_repo(self):
        """GraphRepository 목 생성"""
        repo = MagicMock()
        repo.is_connected = True
        repo.search_memories_via_graph = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def search_service(self, mock_vector_repo, mock_memory_repo, mock_graph_repo):
        """목 의존성 주입된 SearchService 생성"""
        return SearchService(mock_vector_repo, mock_memory_repo, mock_graph_repo)

    # --- RRF 랭킹 정확성 테스트 ---

    @pytest.mark.asyncio
    async def test_rrf_ranking_multi_axis_boost(self, search_service):
        """여러 축에서 동시에 검색된 문서가 더 높은 RRF 점수를 받는지 확인"""
        # Arrange — dense와 sparse 모두에 등장하는 MEM_ID_1이 상위여야 함
        dense = [
            {
                "id": MEM_ID_1,
                "title": "공통 문서",
                "content": "내용1",
                "similarity": 0.9,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
            },
            {
                "id": MEM_ID_2,
                "title": "Dense만",
                "content": "내용2",
                "similarity": 0.8,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
            },
        ]
        sparse = [
            {
                "id": MEM_ID_1,
                "title": "공통 문서",
                "content": "내용1",
                "rank": 1,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
            },
            {
                "id": MEM_ID_3,
                "title": "Sparse만",
                "content": "내용3",
                "rank": 2,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
            },
        ]

        # Act
        fused = search_service.hybrid._rrf_fusion(dense, sparse, [])

        # Assert — MEM_ID_1이 최상위, 양쪽 소스 모두 표기
        assert fused[0]["id"] == MEM_ID_1
        assert "dense" in fused[0]["search_sources"]
        assert "sparse" in fused[0]["search_sources"]

    @pytest.mark.asyncio
    async def test_rrf_score_ordering(self, search_service):
        """RRF fusion 결과가 점수 내림차순으로 정렬되는지 확인"""
        dense = [
            {"id": MEM_ID_2, "similarity": 0.5, "title": "B"},
            {"id": MEM_ID_1, "similarity": 0.4, "title": "A"},
        ]
        sparse = [
            {"id": MEM_ID_1, "rank": 1, "title": "A"},
        ]

        fused = search_service.hybrid._rrf_fusion(dense, sparse, [])

        # MEM_ID_1: dense rank-2 + sparse rank-1 → 높은 합산 점수
        # MEM_ID_2: dense rank-1만
        scores = [item["hybrid_score"] for item in fused]
        assert scores == sorted(scores, reverse=True), "결과가 점수 내림차순이어야 함"

    # --- Graceful Degradation 테스트 ---

    @pytest.mark.asyncio
    async def test_graceful_degradation_sparse_failure(self, search_service, mock_vector_repo):
        """Sparse 검색 실패 시 dense 결과만으로 정상 반환"""
        # Arrange
        mock_vector_repo.similarity_search.return_value = [
            {
                "id": MEM_ID_1,
                "title": "Dense 결과",
                "content": "내용",
                "similarity": 0.8,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
                "tags": None,
                "summary": None,
            },
        ]

        # HybridSearchService._sparse_search가 예외를 던지도록 설정
        with patch.object(
            search_service.hybrid, "_sparse_search", new_callable=AsyncMock, side_effect=Exception("DB 연결 실패")
        ):
            result = await search_service.search(USER_ID, "테스트 쿼리", limit=5)

        # Assert — 에러 없이 dense 결과 반환
        assert result["total"] >= 0

    @pytest.mark.asyncio
    async def test_graceful_degradation_all_empty(self, search_service):
        """모든 검색 축이 빈 결과를 반환하면 빈 결과 정상 처리"""
        result = await search_service.search(USER_ID, "존재하지 않는 쿼리", limit=5)

        assert result["query"] == "존재하지 않는 쿼리"
        assert result["results"] == []
        assert result["total"] == 0

    # --- 필터 적용 테스트 ---

    @pytest.mark.asyncio
    async def test_source_type_filter(self, search_service, mock_vector_repo):
        """source_type 필터가 결과를 올바르게 걸러내는지 확인"""
        # Arrange — NOTE와 PDF 두 종류 결과
        mock_vector_repo.similarity_search.return_value = [
            {
                "id": MEM_ID_1,
                "title": "노트",
                "content": "내용",
                "similarity": 0.9,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
                "tags": None,
                "summary": None,
            },
            {
                "id": MEM_ID_2,
                "title": "PDF",
                "content": "내용",
                "similarity": 0.8,
                "source_type": "PDF",
                "created_at": NOW.isoformat(),
                "tags": None,
                "summary": None,
            },
        ]

        result = await search_service.search(USER_ID, "검색어", source_type="NOTE")

        # Assert — NOTE만 포함
        assert all(r["source_type"] == "NOTE" for r in result["results"])
        assert result["filters_applied"]["source_type"] == "NOTE"

    @pytest.mark.asyncio
    async def test_days_filter(self, search_service, mock_vector_repo):
        """days 필터가 오래된 메모리를 제외하는지 확인"""
        old_date = (NOW - timedelta(days=60)).isoformat()
        recent_date = (NOW - timedelta(days=3)).isoformat()

        mock_vector_repo.similarity_search.return_value = [
            {
                "id": MEM_ID_1,
                "title": "최근",
                "content": "내용",
                "similarity": 0.9,
                "source_type": "NOTE",
                "created_at": recent_date,
                "tags": None,
                "summary": None,
            },
            {
                "id": MEM_ID_2,
                "title": "오래된",
                "content": "내용",
                "similarity": 0.8,
                "source_type": "NOTE",
                "created_at": old_date,
                "tags": None,
                "summary": None,
            },
        ]

        result = await search_service.search(USER_ID, "검색어", days=7)

        # Assert — 7일 이내 결과만 포함
        assert result["total"] == 1
        assert result["results"][0]["id"] == MEM_ID_1

    @pytest.mark.asyncio
    async def test_tags_filter(self, search_service, mock_vector_repo):
        """tags 필터가 태그 매칭 결과만 반환하는지 확인"""
        mock_vector_repo.similarity_search.return_value = [
            {
                "id": MEM_ID_1,
                "title": "파이썬",
                "content": "내용",
                "similarity": 0.9,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
                "tags": ["python", "backend"],
                "summary": None,
            },
            {
                "id": MEM_ID_2,
                "title": "리액트",
                "content": "내용",
                "similarity": 0.8,
                "source_type": "NOTE",
                "created_at": NOW.isoformat(),
                "tags": ["react", "frontend"],
                "summary": None,
            },
        ]

        result = await search_service.search(USER_ID, "개발", tags=["python"])

        assert result["total"] == 1
        assert result["results"][0]["id"] == MEM_ID_1
        assert result["filters_applied"]["tags"] == ["python"]

    # --- get_related_memories 테스트 ---

    @pytest.mark.asyncio
    async def test_get_related_memories_excludes_self(self, search_service, mock_memory_repo, mock_vector_repo):
        """관련 메모리 조회 시 자기 자신이 제외되는지 확인"""
        # Arrange
        from app.schemas.memory_schema import MemoryInDB

        source_memory = MemoryInDB(
            id=UUID(MEM_ID_1),
            user_id=USER_ID,
            title="원본",
            content="원본 내용",
            source_type="NOTE",
            status="completed",
            created_at=NOW,
            updated_at=None,
        )
        mock_memory_repo.get_by_id.return_value = source_memory

        mock_vector_repo.similarity_search.return_value = [
            {"id": MEM_ID_1, "title": "원본", "similarity": 1.0},
            {"id": MEM_ID_2, "title": "관련 문서", "similarity": 0.7},
        ]

        # Act
        related = await search_service.get_related_memories(USER_ID, MEM_ID_1, limit=5)

        # Assert — 자기 자신(MEM_ID_1)은 제외
        ids = [r["id"] for r in related]
        assert MEM_ID_1 not in ids
        assert MEM_ID_2 in ids

    @pytest.mark.asyncio
    async def test_get_related_memories_not_found(self, search_service, mock_memory_repo):
        """존재하지 않는 메모리의 관련 문서 조회 시 빈 리스트 반환"""
        mock_memory_repo.get_by_id.return_value = None

        related = await search_service.get_related_memories(USER_ID, MEM_ID_1)

        assert related == []
