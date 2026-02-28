"""Socrates 노드 단위 테스트 — LangGraph 1.0 파이프라인"""

from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from app.agents.socrates.state import SocratesState, build_socrates_initial_state

# ---------------------------------------------------------------------------
# 헬퍼: 기본 상태 생성
# ---------------------------------------------------------------------------


def _base_state(**overrides) -> SocratesState:
    """테스트용 기본 SocratesState 반환."""
    state = build_socrates_initial_state(
        messages=[HumanMessage(content="테스트 질문")],
        user_id="00000000-0000-0000-0000-000000000001",
        session_id="00000000-0000-0000-0000-000000000010",
        user_query="테스트 질문",
        turn_count=1,
    )
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# query_understanding 노드 테스트
# ---------------------------------------------------------------------------


class TestQueryUnderstandingNode:
    """의도 분류 + 쿼리 재작성 노드 테스트."""

    def test_detect_intent_counter(self):
        """반론 키워드 감지."""
        from app.agents.socrates.nodes.query_understanding import _detect_intent

        assert _detect_intent("이 주장에 대한 반론이 있을까요?") == "counter"

    def test_detect_intent_summary(self):
        """요약 키워드 감지."""
        from app.agents.socrates.nodes.query_understanding import _detect_intent

        assert _detect_intent("이 내용을 요약해줘") == "summary"

    def test_detect_intent_evening(self):
        """저녁 회고 키워드 감지."""
        from app.agents.socrates.nodes.query_understanding import _detect_intent

        assert _detect_intent("오늘 하루를 마무리하고 싶어") == "evening"

    def test_detect_intent_none(self):
        """분류 불가 시 None 반환."""
        from app.agents.socrates.nodes.query_understanding import _detect_intent

        assert _detect_intent("오늘 날씨가 좋네요") is None

    def test_detect_intent_dialectic(self):
        """변증법 키워드 감지."""
        from app.agents.socrates.nodes.query_understanding import _detect_intent

        assert _detect_intent("A vs B 비교해줘") == "dialectic"

    @pytest.mark.asyncio
    async def test_rewrite_query_single_message(self):
        """메시지가 1개이면 재작성 없이 원본 반환."""
        from app.agents.socrates.nodes.query_understanding import _rewrite_query

        messages = [HumanMessage(content="함수형 프로그래밍이란?")]
        result = await _rewrite_query(messages, "함수형 프로그래밍이란?")
        assert result == ["함수형 프로그래밍이란?"]

    @pytest.mark.asyncio
    async def test_query_understanding_node_explicit_mode(self):
        """explicit_mode가 있으면 자동 분류를 건너뛴다."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        state = _base_state(explicit_mode="insight")

        with (
            patch("app.agents.socrates.nodes.query_understanding._rewrite_query", return_value=["테스트 질문"]),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(state)

        assert result["detected_mode"] == "insight"
        assert result["rewritten_queries"] == ["테스트 질문"]
        assert result["search_query"] == "테스트 질문"

    @pytest.mark.asyncio
    async def test_query_understanding_node_auto_detect(self):
        """explicit_mode 없으면 키워드 기반 자동 분류."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        state = _base_state(
            user_query="이 논증의 반론을 알려줘",
            explicit_mode=None,
        )

        with (
            patch(
                "app.agents.socrates.nodes.query_understanding._rewrite_query", return_value=["이 논증의 반론을 알려줘"]
            ),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(state)

        assert result["detected_mode"] == "counter"


# ---------------------------------------------------------------------------
# grading 노드 테스트
# ---------------------------------------------------------------------------


class TestGradingNode:
    """관련성 평가 노드 테스트."""

    @pytest.mark.asyncio
    async def test_grading_empty_memories_returns_empty(self):
        """검색 결과 없으면 quality='retry' (attempts < MAX)."""
        from app.agents.socrates.nodes.grading import grading_node

        state = _base_state(
            raw_memories=[],
            retrieval_attempts=0,
            search_query="테스트",
        )

        with (
            patch("app.agents.socrates.nodes.grading._grade_relevance", return_value=([], False)),
            patch("app.agents.socrates.nodes.grading.get_stream_writer", return_value=lambda x: None),
        ):
            result = await grading_node(state)

        assert result["retrieval_quality"] == "retry"
        assert result["graded_memories"] == []

    @pytest.mark.asyncio
    async def test_grading_with_memories_returns_good(self):
        """관련 기억이 있으면 quality='good'."""
        from app.agents.socrates.nodes.grading import grading_node

        memories = [{"id": "1", "title": "테스트", "content": "내용"}]
        state = _base_state(
            raw_memories=memories,
            retrieval_attempts=1,
            search_query="테스트",
        )

        with (
            patch("app.agents.socrates.nodes.grading._grade_relevance", return_value=(memories, False)),
            patch("app.agents.socrates.nodes.grading.get_stream_writer", return_value=lambda x: None),
        ):
            result = await grading_node(state)

        assert result["retrieval_quality"] == "good"
        assert len(result["graded_memories"]) == 1

    @pytest.mark.asyncio
    async def test_grading_max_attempts_returns_empty(self):
        """최대 재시도 도달 시 quality='empty'."""
        from app.agents.socrates.nodes.grading import grading_node

        state = _base_state(
            raw_memories=[],
            retrieval_attempts=2,  # MAX_RETRIEVAL_ATTEMPTS == 2
            search_query="테스트",
        )

        with (
            patch("app.agents.socrates.nodes.grading._grade_relevance", return_value=([], False)),
            patch("app.agents.socrates.nodes.grading.get_stream_writer", return_value=lambda x: None),
        ):
            result = await grading_node(state)

        assert result["retrieval_quality"] == "empty"


# ---------------------------------------------------------------------------
# context_assembly 노드 테스트
# ---------------------------------------------------------------------------


class TestContextAssemblyNode:
    """시스템 프롬프트 조립 노드 테스트."""

    @pytest.mark.asyncio
    async def test_context_assembly_empty_state(self):
        """최소 상태로 context_assembly_node 실행 — system_prompt 생성 확인."""
        from app.agents.socrates.nodes.context_assembly import context_assembly_node

        state = _base_state()

        with patch("app.agents.socrates.nodes.context_assembly.get_stream_writer", return_value=lambda x: None):
            result = await context_assembly_node(state)

        assert "system_prompt" in result
        assert len(result["system_prompt"]) > 0
        assert "llm_messages" in result
        assert len(result["llm_messages"]) >= 1  # SystemMessage + messages
        assert "references" in result
        assert result["references"] == []

    @pytest.mark.asyncio
    async def test_context_assembly_with_memories(self):
        """graded_memories가 있으면 references에 포함."""
        from app.agents.socrates.nodes.context_assembly import context_assembly_node

        memories = [
            {
                "id": "abc-123",
                "title": "기억 제목",
                "source_type": "NOTE",
                "created_at": "2026-01-01T00:00:00",
            }
        ]
        state = _base_state(
            graded_memories=memories,
            formatted_memories="--- 기억 #1 [2026-01-01] 기억 제목 ---\n내용",
        )

        with patch("app.agents.socrates.nodes.context_assembly.get_stream_writer", return_value=lambda x: None):
            result = await context_assembly_node(state)

        assert len(result["references"]) == 1
        assert result["references"][0]["id"] == "abc-123"
        assert result["references"][0]["title"] == "기억 제목"

    @pytest.mark.asyncio
    async def test_context_assembly_max_5_references(self):
        """graded_memories가 6개여도 references는 최대 5개."""
        from app.agents.socrates.nodes.context_assembly import context_assembly_node

        memories = [
            {"id": str(i), "title": f"기억 {i}", "source_type": "NOTE", "created_at": "2026-01-01"} for i in range(6)
        ]
        state = _base_state(graded_memories=memories)

        with patch("app.agents.socrates.nodes.context_assembly.get_stream_writer", return_value=lambda x: None):
            result = await context_assembly_node(state)

        assert len(result["references"]) == 5


# ---------------------------------------------------------------------------
# SocratesState 초기화 테스트
# ---------------------------------------------------------------------------


class TestSocratesState:
    """SocratesState 초기화 함수 테스트."""

    def test_build_initial_state_defaults(self):
        """build_socrates_initial_state 기본값 확인."""
        state = build_socrates_initial_state(
            messages=[HumanMessage(content="안녕")],
            user_id="user-1",
            session_id="session-1",
            user_query="안녕",
            turn_count=1,
        )
        assert state["user_id"] == "user-1"
        assert state["session_id"] == "session-1"
        assert state["user_query"] == "안녕"
        assert state["search_query"] == "안녕"
        assert state["retrieval_attempts"] == 0
        assert state["raw_memories"] == []
        assert state["graded_memories"] == []
        assert state["retrieval_quality"] == "empty"
        assert state["detected_mode"] is None
        assert state["explicit_mode"] is None

    def test_build_initial_state_with_mode(self):
        """explicit_mode 전달 시 상태에 반영."""
        state = build_socrates_initial_state(
            messages=[HumanMessage(content="요약해줘")],
            user_id="user-1",
            session_id="session-1",
            user_query="요약해줘",
            turn_count=1,
            mode="summary",
        )
        assert state["explicit_mode"] == "summary"


# ---------------------------------------------------------------------------
# graph 라우팅 함수 테스트
# ---------------------------------------------------------------------------


class TestGraphRouting:
    """graph.py route_after_grading 함수 테스트."""

    def test_route_retry(self):
        """retrieval_quality='retry' → memory_retrieval 재실행."""
        from app.agents.socrates.graph import route_after_grading

        state = _base_state(retrieval_quality="retry")
        assert route_after_grading(state) == "memory_retrieval"

    def test_route_good(self):
        """retrieval_quality='good' → enrichment 진행."""
        from app.agents.socrates.graph import route_after_grading

        state = _base_state(retrieval_quality="good")
        assert route_after_grading(state) == "enrichment"

    def test_route_empty(self):
        """retrieval_quality='empty' → enrichment 진행."""
        from app.agents.socrates.graph import route_after_grading

        state = _base_state(retrieval_quality="empty")
        assert route_after_grading(state) == "enrichment"
