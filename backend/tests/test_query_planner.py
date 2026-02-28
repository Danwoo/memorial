"""query_planner_node 검색 전략 분류 단위 테스트."""

from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from app.agents.socrates.state import SocratesState, build_socrates_initial_state


def _state(query: str, turn_count: int = 1, mode: str | None = None) -> SocratesState:
    """테스트용 기본 상태 생성."""
    state = build_socrates_initial_state(
        messages=[HumanMessage(content=query)],
        user_id="00000000-0000-0000-0000-000000000001",
        session_id="00000000-0000-0000-0000-000000000010",
        user_query=query,
        turn_count=turn_count,
    )
    if mode:
        state["detected_mode"] = mode
    return state


# ---------------------------------------------------------------------------
# no_retrieval 분류 테스트
# ---------------------------------------------------------------------------


class TestNoRetrieval:
    """인사/감사/단순 확인 → no_retrieval."""

    @pytest.mark.asyncio
    async def test_greeting_korean(self):
        """한국어 인사 → no_retrieval."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("안녕"))

        assert result["retrieval_plan"] == "no_retrieval"

    @pytest.mark.asyncio
    async def test_greeting_english(self):
        """영어 인사 → no_retrieval."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("hi"))

        assert result["retrieval_plan"] == "no_retrieval"

    @pytest.mark.asyncio
    async def test_thanks_korean(self):
        """감사 표현 → no_retrieval."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("고마워"))

        assert result["retrieval_plan"] == "no_retrieval"

    @pytest.mark.asyncio
    async def test_simple_ack(self):
        """단순 확인 → no_retrieval."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("응"))

        assert result["retrieval_plan"] == "no_retrieval"


# ---------------------------------------------------------------------------
# deep_diary 분류 테스트
# ---------------------------------------------------------------------------


class TestDeepDiary:
    """감정/일기 키워드 + 초반 턴 → deep_diary."""

    @pytest.mark.asyncio
    async def test_emotion_keyword_early_turn(self):
        """감정 키워드 + 턴 1 → deep_diary."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("오늘 기분이 우울해", turn_count=1))

        assert result["retrieval_plan"] == "deep_diary"

    @pytest.mark.asyncio
    async def test_diary_keyword(self):
        """다이어리 키워드 → deep_diary."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("일기 쓰고 싶어", turn_count=2))

        assert result["retrieval_plan"] == "deep_diary"

    @pytest.mark.asyncio
    async def test_evening_mode(self):
        """evening 모드 → deep_diary."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("오늘 하루 어땠어?", turn_count=1, mode="evening"))

        assert result["retrieval_plan"] == "deep_diary"

    @pytest.mark.asyncio
    async def test_emotion_keyword_late_turn_not_deep_diary(self):
        """감정 키워드여도 턴 > 2이면 deep_diary 아님."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("우울한 감정에 대해", turn_count=5))

        # 늦은 턴에서는 simple_search 또는 full_rag
        assert result["retrieval_plan"] in ("simple_search", "full_rag")


# ---------------------------------------------------------------------------
# simple_search 분류 테스트
# ---------------------------------------------------------------------------


class TestSimpleSearch:
    """짧고 단순한 쿼리 → simple_search."""

    @pytest.mark.asyncio
    async def test_short_query(self):
        """30자 미만 단순 쿼리 → simple_search."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("파이썬 뭐야", turn_count=3))

        assert result["retrieval_plan"] == "simple_search"

    @pytest.mark.asyncio
    async def test_counter_mode_not_simple(self):
        """counter 모드 → simple_search 아님 (full_rag)."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("반론", turn_count=3, mode="counter"))

        assert result["retrieval_plan"] == "full_rag"


# ---------------------------------------------------------------------------
# full_rag 분류 테스트
# ---------------------------------------------------------------------------


class TestFullRag:
    """복잡한 쿼리 → full_rag."""

    @pytest.mark.asyncio
    async def test_long_complex_query(self):
        """30자 이상 복잡한 쿼리 → full_rag."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(
                _state("함수형 프로그래밍과 객체지향의 장단점을 내 스크랩 기반으로 정리해줘", turn_count=3)
            )

        assert result["retrieval_plan"] == "full_rag"

    @pytest.mark.asyncio
    async def test_dialectic_mode_always_full_rag(self):
        """dialectic 모드 → full_rag."""
        from app.agents.shared.query_planner import query_planner_node

        with patch("app.agents.shared.query_planner.get_stream_writer", return_value=lambda x: None):
            result = await query_planner_node(_state("비교", turn_count=3, mode="dialectic"))

        assert result["retrieval_plan"] == "full_rag"
