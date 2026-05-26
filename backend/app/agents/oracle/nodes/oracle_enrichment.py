import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.oracle.state import OracleState
from app.agents.shared.enrichment_utils import (
    format_connection_suggestion,
    format_memories_with_budget,
    get_previous_session_context,
    search_connection_suggestion,
)

logger = logging.getLogger(__name__)

CONNECTION_TURN_INTERVAL = 3

# LLM 분류 결과(detected_mode)로 에이전트 전환 제안 판단
_SOCRATES_MODES = {"evening", "insight", "assumption", "five_whys"}
_LIBRARIAN_MODES = {"connection", "compare", "deep_dive"}


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
    detected_mode = state.get("detected_mode")
    retrieval_plan = state.get("retrieval_plan", "full_rag")

    vector_repo = runtime.context.vector_repo
    chat_repo = runtime.context.chat_repo

    # 1. 메모리 포맷팅
    formatted_memories = format_memories_with_budget(graded_memories, item_label="자료")

    # 2. LLM 분류 결과로 에이전트 전환 제안 (contradiction_context 필드 재활용)
    contradiction_context = ""
    if detected_mode in _SOCRATES_MODES or retrieval_plan == "deep_diary":
        contradiction_context = "[Oracle 제안] 다이어리 뷰의 Socrates에서 더 깊은 감정 탐색이 가능합니다."
    elif detected_mode in _LIBRARIAN_MODES:
        contradiction_context = "[Oracle 제안] 스크랩 뷰의 Librarian에서 더 체계적으로 탐색할 수 있습니다."

    # 3. 연결 제안 (3턴 간격)
    connection_suggestion = ""
    if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
        referenced_ids = {m.get("id") for m in graded_memories}
        suggestion = await search_connection_suggestion(search_query, user_id, referenced_ids, vector_repo)
        if suggestion:
            connection_suggestion = format_connection_suggestion(suggestion)

    # 4. 이전 세션 컨텍스트 (첫 턴)
    previous_session_context = ""
    if turn_count == 1:
        previous_session_context = await get_previous_session_context(UUID(user_id), chat_repo)

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
