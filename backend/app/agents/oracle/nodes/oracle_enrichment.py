import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.oracle.state import OracleState
from app.agents.shared.enrichment_utils import (
    format_memories_with_budget,
    get_previous_session_context,
    search_connection_suggestion,
)

logger = logging.getLogger(__name__)

CONNECTION_TURN_INTERVAL = 3

# Oracle 에이전트 전환 제안 키워드
_DIARY_KEYWORDS = ["일기", "다이어리", "감정", "오늘 하루", "기분", "느낌", "마음", "힘들", "슬프", "기쁘"]
_SCRAP_KEYWORDS = ["스크랩", "저장한", "아티클", "링크", "기사", "요약", "정리", "연결", "관계"]


def _detect_agent_switch_suggestion(message: str) -> str | None:
    """사용자 메시지에서 에이전트 전환 힌트를 감지."""
    msg = message.lower()
    if any(kw in msg for kw in _DIARY_KEYWORDS):
        return "socrates"
    if any(kw in msg for kw in _SCRAP_KEYWORDS):
        return "librarian"
    return None


async def oracle_enrichment_node(state: OracleState, runtime: Runtime[AgentContext]) -> dict:
    """Oracle 범용 추가 컨텍스트 수집 + 에이전트 전환 감지 노드.

    1. formatted_memories: graded_memories를 RRF 가변 할당 포맷
    2. connection_suggestion: 3턴 간격 연결 제안
    3. agent_switch_suggestion: 다이어리/스크랩 관련 질문 시 전환 제안 (contradiction_context 활용)
    4. previous_session_context: 첫 턴 이전 세션 요약
    5. user_profile: 개인화 프로필
    """
    writer = get_stream_writer()
    writer({"node": "oracle_enrichment", "status": "started"})

    user_id = state["user_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    turn_count = state.get("turn_count", 0)

    vector_repo = runtime.context.vector_repo
    socrates_repo = runtime.context.socrates_repo

    # 1. 메모리 포맷팅
    formatted_memories = format_memories_with_budget(graded_memories)

    # 2. 에이전트 전환 제안 감지 (contradiction_context 필드 재활용)
    contradiction_context = ""
    switch_target = _detect_agent_switch_suggestion(user_query)
    if switch_target == "socrates":
        contradiction_context = (
            "[Oracle 제안] 이 주제는 다이어리 뷰의 Socrates 에이전트에서 더 깊은 감정 탐색이 가능합니다."
        )
    elif switch_target == "librarian":
        contradiction_context = (
            "[Oracle 제안] 저장하신 스크랩 탐색은 스크랩 뷰의 Librarian 에이전트에서 더 체계적으로 할 수 있습니다."
        )

    # 3. 연결 제안 (3턴 간격)
    connection_suggestion = ""
    if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
        referenced_ids = {m.get("id") for m in graded_memories}
        suggestion = await search_connection_suggestion(search_query, user_id, referenced_ids, vector_repo)
        if suggestion:
            date = suggestion.get("created_at", "")[:10]
            title = suggestion.get("title", "Untitled")
            summary = suggestion.get("summary") or suggestion.get("content", "")[:200]
            connection_suggestion = f"[{date}] {title}: {summary}"

    # 4. 이전 세션 컨텍스트 (첫 턴)
    previous_session_context = ""
    if turn_count == 1:
        previous_session_context = await get_previous_session_context(UUID(user_id), socrates_repo)

    # 5. 사용자 프로필
    user_profile = None
    try:
        from app.services.user_profile_service import get_user_profile

        user_profile = await get_user_profile(user_id)
    except Exception:
        logger.warning("Oracle user_profile 조회 실패")

    writer({"node": "oracle_enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": "",
    }
