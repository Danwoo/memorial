"""query_understanding_node LLM 기반 통합 쿼리 분석 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from app.agents.socrates.state import SocratesState, build_socrates_initial_state


def _state(query: str, turn_count: int = 1, explicit_mode: str | None = None) -> SocratesState:
    """테스트용 기본 상태 생성."""
    state = build_socrates_initial_state(
        messages=[HumanMessage(content=query)],
        user_id="00000000-0000-0000-0000-000000000001",
        session_id="00000000-0000-0000-0000-000000000010",
        user_query=query,
        turn_count=turn_count,
    )
    if explicit_mode:
        state["explicit_mode"] = explicit_mode
    return state


def _mock_llm_response(json_str: str):
    """LLM 응답을 모킹하는 헬퍼."""
    mock_response = MagicMock()
    mock_response.content = json_str
    mock_llm = MagicMock()
    mock_llm_bound = MagicMock()
    mock_llm_bound.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm.bind = MagicMock(return_value=mock_llm_bound)
    return mock_llm


# ---------------------------------------------------------------------------
# no_retrieval 분류 테스트
# ---------------------------------------------------------------------------


class TestNoRetrieval:
    """LLM이 no_retrieval 반환 시 동작 확인."""

    @pytest.mark.asyncio
    async def test_greeting_no_retrieval(self):
        """LLM이 no_retrieval 분류 → 상태에 반영."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response('{"mode": null, "retrieval_plan": "no_retrieval", "search_queries": ["안녕"]}')

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("안녕"))

        assert result["retrieval_plan"] == "no_retrieval"
        assert result["detected_mode"] is None
        assert result["search_query"] == "안녕"

    @pytest.mark.asyncio
    async def test_simple_ack_no_retrieval(self):
        """단순 확인 → no_retrieval."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response('{"mode": null, "retrieval_plan": "no_retrieval", "search_queries": ["응"]}')

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("응"))

        assert result["retrieval_plan"] == "no_retrieval"


# ---------------------------------------------------------------------------
# deep_diary 분류 테스트
# ---------------------------------------------------------------------------


class TestDeepDiary:
    """LLM이 deep_diary 분류 시 동작 확인."""

    @pytest.mark.asyncio
    async def test_emotional_deep_diary(self):
        """감정 표현 → LLM이 deep_diary 분류 → 상태에 반영."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response(
            '{"mode": null, "retrieval_plan": "deep_diary", "search_queries": ["발표 실패 후 창피함"]}'
        )

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("오늘 발표 완전 망했어", turn_count=1))

        assert result["retrieval_plan"] == "deep_diary"

    @pytest.mark.asyncio
    async def test_deep_diary_turn_gating(self):
        """LLM이 deep_diary 반환해도 turn_count > 2이면 full_rag로 강등."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response(
            '{"mode": null, "retrieval_plan": "deep_diary", "search_queries": ["우울한 감정"]}'
        )

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("우울한 감정에 대해", turn_count=5))

        assert result["retrieval_plan"] == "full_rag"


# ---------------------------------------------------------------------------
# explicit_mode 오버라이드 테스트
# ---------------------------------------------------------------------------


class TestExplicitModeOverride:
    """explicit_mode가 있으면 LLM 분류 mode를 오버라이드."""

    @pytest.mark.asyncio
    async def test_explicit_mode_overrides_llm(self):
        """explicit_mode=insight 전달 → detected_mode가 insight로 오버라이드."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        # LLM이 null 반환해도 explicit_mode로 오버라이드
        mock_llm = _mock_llm_response('{"mode": null, "retrieval_plan": "full_rag", "search_queries": ["테스트 질문"]}')

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("테스트 질문", explicit_mode="insight"))

        assert result["detected_mode"] == "insight"


# ---------------------------------------------------------------------------
# LLM 실패 폴백 테스트
# ---------------------------------------------------------------------------


class TestLLMFailureFallback:
    """LLM 예외 → 안전 폴백."""

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self):
        """LLM 예외 발생 → full_rag 폴백, detected_mode=None."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = MagicMock()
        mock_llm_bound = MagicMock()
        mock_llm_bound.ainvoke = AsyncMock(side_effect=Exception("LLM 오류"))
        mock_llm.bind = MagicMock(return_value=mock_llm_bound)

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("복잡한 질문"))

        assert result["retrieval_plan"] == "full_rag"
        assert result["detected_mode"] is None
        assert result["search_query"] == "복잡한 질문"


# ---------------------------------------------------------------------------
# 모드 분류 테스트
# ---------------------------------------------------------------------------


class TestModeClassification:
    """LLM이 다양한 mode를 반환할 때 올바르게 처리."""

    @pytest.mark.asyncio
    async def test_counter_mode_full_rag(self):
        """반론 모드 분류 → counter + full_rag."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response(
            '{"mode": "counter", "retrieval_plan": "full_rag", "search_queries": ["주장에 대한 반론"]}'
        )

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("이 주장에 반론 있어?"))

        assert result["detected_mode"] == "counter"
        assert result["retrieval_plan"] == "full_rag"

    @pytest.mark.asyncio
    async def test_comparison_splits_queries(self):
        """비교 요청 → 2개 쿼리 분리."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response(
            '{"mode": "dialectic", "retrieval_plan": "full_rag", "search_queries": ["함수형 프로그래밍 장점", "OOP 장점"]}'
        )

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("함수형 vs OOP 비교"))

        assert result["detected_mode"] == "dialectic"
        assert len(result["rewritten_queries"]) == 2
        assert result["search_query"] == "함수형 프로그래밍 장점"

    @pytest.mark.asyncio
    async def test_invalid_mode_fallback(self):
        """유효하지 않은 mode → None으로 처리."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response(
            '{"mode": "invalid_mode_xyz", "retrieval_plan": "full_rag", "search_queries": ["질문"]}'
        )

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("질문"))

        assert result["detected_mode"] is None

    @pytest.mark.asyncio
    async def test_invalid_plan_fallback(self):
        """유효하지 않은 retrieval_plan → full_rag 폴백."""
        from app.agents.socrates.nodes.query_understanding import query_understanding_node

        mock_llm = _mock_llm_response('{"mode": null, "retrieval_plan": "unknown_plan", "search_queries": ["질문"]}')

        with (
            patch("app.agents.socrates.nodes.query_understanding.get_analytical_llm", return_value=mock_llm),
            patch("app.agents.socrates.nodes.query_understanding.get_stream_writer", return_value=lambda x: None),
        ):
            result = await query_understanding_node(_state("질문"))

        assert result["retrieval_plan"] == "full_rag"
