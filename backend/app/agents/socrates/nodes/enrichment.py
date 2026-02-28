import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.shared.enrichment_utils import (
    build_contradiction_context,
    format_connection_suggestion,
    format_memories_with_budget,
    get_previous_session_context,
    get_topic_session_context,
    search_connection_suggestion,
)
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)

# 연결 제안 설정
CONNECTION_TURN_INTERVAL = 3


async def enrichment_node(state: SocratesState, runtime: Runtime[AgentContext]) -> dict:
    """모드별 추가 컨텍스트 수집 + 메모리 포맷팅 노드 (Runtime DI 적용).

    1. formatted_memories: graded_memories를 RRF 가중 할당으로 포맷
    2. contradiction_context: counter 모드일 때 반론 검색
    3. connection_suggestion: turn_count % 3 == 0 일 때 연결 제안
    4. previous_session_context / topic_session_context: 첫 턴일 때만
    5. user_profile: 개인화 프로필 조회
    """
    writer = get_stream_writer()
    writer({"node": "enrichment", "status": "started"})

    user_id = state["user_id"]
    session_id = state["session_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    detected_mode = state.get("detected_mode")
    turn_count = state.get("turn_count", 0)
    source_context = state.get("source_context")

    vector_repo = runtime.context.vector_repo
    socrates_repo = runtime.context.socrates_repo

    # 1. 메모리 포맷팅
    formatted_memories = format_memories_with_budget(graded_memories)

    # 2. counter 모드 반론 컨텍스트
    contradiction_context = ""
    if detected_mode == "counter" and graded_memories:
        contradiction_context = await build_contradiction_context(search_query, graded_memories, user_id, vector_repo)

    # 3. 연결 제안 (3턴 간격)
    connection_suggestion = ""
    if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
        referenced_ids = {m.get("id") for m in graded_memories}
        suggestion = await search_connection_suggestion(search_query, user_id, referenced_ids, vector_repo)
        if suggestion:
            connection_suggestion = format_connection_suggestion(suggestion)
            logger.debug("연결 제안 발견: %s", suggestion.get("title", ""))

    # 4. 이전 세션 / 주제 세션 컨텍스트 (첫 턴일 때만)
    previous_session_context = ""
    topic_session_context = ""
    if turn_count == 1:
        user_uuid = UUID(user_id)
        previous_session_context = await get_previous_session_context(user_uuid, socrates_repo)

        if source_context and source_context.get("tags"):
            topic_session_context = await get_topic_session_context(
                user_uuid,
                source_context["tags"],
                session_id,
                socrates_repo,
            )

    # 5. 사용자 프로필
    user_profile = None
    try:
        from app.services.user_profile_service import get_user_profile

        user_profile = await get_user_profile(user_id)
    except Exception:
        logger.warning("user_profile 조회 실패")

    writer({"node": "enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": topic_session_context,
    }
