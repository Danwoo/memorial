import logging
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.librarian.state import LibrarianChatState
from app.agents.shared.enrichment_utils import (
    build_contradiction_context,
    format_connection_suggestion,
    format_memories_with_budget,
    get_previous_session_context,
    search_connection_suggestion,
)

logger = logging.getLogger(__name__)

# Librarian 전용 연결 발견 임계값 (더 넓은 범위)
CONNECTION_SUGGEST_LOW = 0.75
CONNECTION_SUGGEST_HIGH = 0.92
CONNECTION_TURN_INTERVAL = 2  # Librarian은 2턴마다 연결 제안

# Librarian 스크랩 반론 탐지 설정
SCRAP_CONTRADICTION_SEARCH_LIMIT = 3
SCRAP_CONTRADICTION_THRESHOLD = 0.45
SCRAP_QUERY_SUFFIXES = ["비판", "반론", "단점"]


async def analytical_enrichment_node(state: LibrarianChatState, runtime: Runtime[AgentContext]) -> dict:
    """지식 분석 추가 컨텍스트 수집 노드 (Librarian 에이전트).

    1. formatted_memories: graded_memories를 출처 URL 포함 포맷
    2. contradiction_context: 지식 간 모순 탐지
    3. connection_suggestion: 2턴 간격 연결 발견
    4. previous_session_context: 이전 탐색 세션 요약
    5. user_profile: 관심 태그 기반 개인화
    """
    writer = get_stream_writer()
    writer({"node": "analytical_enrichment", "status": "started"})

    user_id = state["user_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    detected_mode = state.get("detected_mode")
    turn_count = state.get("turn_count", 0)

    vector_repo = runtime.context.vector_repo
    chat_repo = runtime.context.chat_repo

    # 1. 스크랩 포맷팅 (출처 URL 포함)
    formatted_memories = format_memories_with_budget(graded_memories, include_url=True, item_label="스크랩")

    # 2. 모순 탐지 (compare/connection 모드 또는 기본)
    contradiction_context = ""
    if graded_memories and detected_mode in ("compare", "connection", None):
        contradiction_context = await build_contradiction_context(
            search_query,
            graded_memories,
            user_id,
            vector_repo,
            search_limit=SCRAP_CONTRADICTION_SEARCH_LIMIT,
            threshold=SCRAP_CONTRADICTION_THRESHOLD,
            query_suffixes=SCRAP_QUERY_SUFFIXES,
        )

    # 3. 연결 제안 (2턴 간격, 넓은 유사도 범위)
    connection_suggestion = ""
    if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
        referenced_ids = {m.get("id") for m in graded_memories}
        suggestion = await search_connection_suggestion(
            search_query,
            user_id,
            referenced_ids,
            vector_repo,
            low_threshold=CONNECTION_SUGGEST_LOW,
            high_threshold=CONNECTION_SUGGEST_HIGH,
        )
        if suggestion:
            connection_suggestion = format_connection_suggestion(suggestion, include_url=True)

    # 4. 이전 세션 컨텍스트 (첫 턴, Librarian 레이블)
    previous_session_context = ""
    if turn_count == 1:
        previous_session_context = await get_previous_session_context(
            UUID(user_id),
            chat_repo,
            limit=2,
            section_title="이전 탐색 요약",
        )

    # 5. 사용자 프로필
    user_profile = None
    try:
        from app.services.user_profile_service import get_user_profile

        user_profile = await get_user_profile(user_id)
    except Exception:
        logger.warning("Librarian user_profile 조회 실패")

    writer({"node": "analytical_enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": "",
    }
