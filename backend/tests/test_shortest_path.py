"""MindmapRepository.find_shortest_path 통합 테스트.

KuzuDB 0.11에서 실제로 path query가 동작하는지 검증.
이전 구현은 Neo4j 표준 `[n IN nodes(p) | n.name]`를 사용해 silent fail이었음.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from app.domain.mindmap import MindmapShortestPath
from app.repositories.mindmap import MindmapRepository


@pytest.fixture
def repo():
    """임시 KuzuDB 인스턴스로 테스트 격리."""
    with tempfile.TemporaryDirectory() as td:
        r = MindmapRepository(db_path=str(Path(td) / "test.kuzu"))

        # 그래프 시드: A → B → C → D, A → D (지름길)
        entities = [
            {"name": "A", "type": "Concept"},
            {"name": "B", "type": "Concept"},
            {"name": "C", "type": "Concept"},
            {"name": "D", "type": "Concept"},
        ]
        relations = [
            {"source": "A", "target": "B", "type": "USES"},
            {"source": "B", "target": "C", "type": "USES"},
            {"source": "C", "target": "D", "type": "USES"},
            {"source": "A", "target": "D", "type": "IS_A"},  # 1-hop 지름길
        ]
        asyncio.run(r.save_entities(entities, "src1", "user1"))
        asyncio.run(r.save_relations(relations))
        yield r


@pytest.mark.asyncio
async def test_finds_direct_path(repo):
    """1-hop 직접 연결을 찾는다."""
    result = await repo.find_shortest_path("A", "B", user_id="user1", max_hops=3)
    assert result is not None
    assert isinstance(result, MindmapShortestPath)
    assert result.hops == 1
    assert result.names == ["A", "B"] or result.names == ["B", "A"]  # undirected


@pytest.mark.asyncio
async def test_picks_shortest_over_alternatives(repo):
    """A → D는 직접 IS_A 1-hop과 A→B→C→D 3-hop 두 경로 — 1-hop 선택해야."""
    result = await repo.find_shortest_path("A", "D", user_id="user1", max_hops=3)
    assert result is not None
    assert result.hops == 1


@pytest.mark.asyncio
async def test_multi_hop_path(repo):
    """B → D는 2-hop (B→C→D)."""
    result = await repo.find_shortest_path("B", "D", user_id="user1", max_hops=3)
    assert result is not None
    assert result.hops == 2


@pytest.mark.asyncio
async def test_returns_none_for_unknown_user(repo):
    """다른 user의 KB에는 entity가 없으므로 None."""
    result = await repo.find_shortest_path("A", "D", user_id="other-user", max_hops=3)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_no_path_within_max_hops(repo):
    """그래프에 없는 엔티티 → None."""
    result = await repo.find_shortest_path("A", "NonExistent", user_id="user1", max_hops=3)
    assert result is None


@pytest.mark.asyncio
async def test_explanation_property(repo):
    """MindmapShortestPath.explanation이 사람이 읽기 좋은 형식."""
    result = await repo.find_shortest_path("A", "B", user_id="user1", max_hops=3)
    assert result is not None
    # 1-hop이면 "A →(USES)→ B" 또는 "B →(USES)→ A" (undirected)
    assert "USES" in result.explanation or "IS_A" in result.explanation
    assert "→" in result.explanation
