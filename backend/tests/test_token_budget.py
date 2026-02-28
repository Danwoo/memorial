"""토큰 예산 관리자 단위 테스트"""

from app.agents.token_budget import enforce_context_budget


class TestEnforceContextBudget:
    """enforce_context_budget 함수 테스트."""

    def test_under_budget_no_change(self):
        """예산 미달 시 원본 그대로 반환."""
        sections = {
            "formatted_memories": "a" * 100,
            "diary_context": "b" * 100,
        }
        result = enforce_context_budget(sections, budget=1000)
        assert result["formatted_memories"] == "a" * 100
        assert result["diary_context"] == "b" * 100

    def test_over_budget_low_priority_trimmed_first(self):
        """예산 초과 시 우선순위 낮은 섹션(topic_session_context)부터 절삭."""
        sections = {
            "formatted_memories": "m" * 500,
            "topic_session_context": "t" * 600,
        }
        result = enforce_context_budget(sections, budget=800)
        # topic_session_context는 우선순위 낮아서 절삭
        total = len(result["formatted_memories"]) + len(result["topic_session_context"])
        assert total <= 800
        # formatted_memories는 최우선이므로 보존
        assert result["formatted_memories"] == "m" * 500

    def test_extreme_single_section_over_budget(self):
        """단일 섹션이 예산 전체를 초과하면 해당 섹션이 잘림."""
        sections = {
            "topic_session_context": "x" * 5000,
        }
        result = enforce_context_budget(sections, budget=1000)
        assert len(result["topic_session_context"]) <= 1000

    def test_original_not_mutated(self):
        """원본 dict가 변경되지 않음."""
        sections = {
            "formatted_memories": "a" * 100,
            "topic_session_context": "t" * 1000,
        }
        original_top = sections["topic_session_context"]
        enforce_context_budget(sections, budget=500)
        # 원본 보존 확인
        assert sections["topic_session_context"] == original_top

    def test_empty_sections_ignored(self):
        """빈 섹션은 절삭 대상에서 제외."""
        sections = {
            "formatted_memories": "m" * 300,
            "community_context": "",
            "topic_session_context": "t" * 300,
        }
        result = enforce_context_budget(sections, budget=400)
        assert result["community_context"] == ""
        total = sum(len(v) for v in result.values())
        assert total <= 400

    def test_unknown_keys_preserved(self):
        """SECTION_PRIORITY에 없는 키는 절삭하지 않음."""
        sections = {
            "topic_session_context": "t" * 600,
            "custom_key": "c" * 600,
        }
        result = enforce_context_budget(sections, budget=700)
        # custom_key는 우선순위 목록에 없으므로 절삭 불가 → 보존
        assert result["custom_key"] == "c" * 600
