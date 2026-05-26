"""도메인 모델 단위 테스트 — 이번 리팩토링으로 도입된 Pydantic 엔티티 검증."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.chat import ChatMessageRecord, ChatSession, ChatSessionSummary
from app.domain.diary import DiaryEntry
from app.domain.mindmap import MindmapEntity, MindmapRelation, MindmapShortestPath

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(UTC)


class TestChatSession:
    def test_create_with_defaults(self):
        s = ChatSession(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            user_id=USER_ID,
            title="Test",
            created_at=NOW,
        )
        assert s.agent_type == "oracle"
        assert s.summary is None
        assert s.topic_tags is None

    def test_with_topic_tags(self):
        s = ChatSession(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            user_id=USER_ID,
            title="Test",
            created_at=NOW,
            topic_tags=["React", "TypeScript"],
        )
        assert s.topic_tags == ["React", "TypeScript"]

    def test_model_copy_update(self):
        s = ChatSession(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            user_id=USER_ID,
            title="Original",
            created_at=NOW,
        )
        s2 = s.model_copy(update={"title": "Updated"})
        assert s2.title == "Updated"
        assert s.title == "Original"  # 원본 불변


class TestChatMessageRecord:
    def test_role_literal_enforced(self):
        m = ChatMessageRecord(role="user", content="안녕", created_at=NOW)
        assert m.role == "user"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValueError):
            ChatMessageRecord(role="invalid", content="x", created_at=NOW)

    def test_frozen(self):
        m = ChatMessageRecord(role="user", content="안녕", created_at=NOW)
        with pytest.raises((ValueError, TypeError)):
            m.role = "assistant"


class TestChatSessionSummary:
    def test_construct(self):
        s = ChatSessionSummary(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            title="Test",
            summary="간단 요약",
            created_at=NOW,
        )
        assert s.summary == "간단 요약"


class TestDiaryEntry:
    def test_defaults(self):
        d = DiaryEntry(
            id=UUID("00000000-0000-0000-0000-000000000020"),
            user_id=USER_ID,
            content="오늘의 일기",
            created_at=NOW,
        )
        assert d.tags == []
        assert d.mood is None
        assert d.updated_at is None

    def test_with_full_fields(self):
        d = DiaryEntry(
            id=UUID("00000000-0000-0000-0000-000000000020"),
            user_id=USER_ID,
            content="내용",
            mood="POSITIVE",
            tags=["a", "b"],
            created_at=NOW,
            updated_at=NOW,
        )
        assert d.mood == "POSITIVE"
        assert len(d.tags) == 2


class TestMindmapDomain:
    def test_entity_default_type(self):
        e = MindmapEntity(name="React")
        assert e.type == "Concept"

    def test_entity_frozen(self):
        e = MindmapEntity(name="React", type="Framework")
        with pytest.raises((ValueError, TypeError)):
            e.name = "Vue"

    def test_relation_default_type(self):
        r = MindmapRelation(source="A", target="B")
        assert r.rel_type == "RELATED_TO"


class TestMindmapShortestPath:
    def test_explanation_format(self):
        p = MindmapShortestPath(
            names=["React", "JavaScript", "Frontend"],
            rel_types=["USES", "PART_OF"],
            hops=2,
        )
        assert "React →(USES)→ JavaScript" in p.explanation
        assert "JavaScript →(PART_OF)→ Frontend" in p.explanation

    def test_explanation_empty_rel_types(self):
        """간선 없는 trivial path는 ' → '로 join."""
        p = MindmapShortestPath(names=["A"], rel_types=[], hops=0)
        assert p.explanation == "A"

    def test_explanation_single_edge(self):
        p = MindmapShortestPath(names=["A", "B"], rel_types=["USES"], hops=1)
        assert p.explanation == "A →(USES)→ B"
