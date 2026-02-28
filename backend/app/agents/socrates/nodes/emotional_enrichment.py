import logging
from uuid import UUID

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from app.agents.base_context import AgentContext
from app.agents.shared.enrichment_utils import (
    format_memories_with_budget,
    get_previous_session_context,
    get_topic_session_context,
    search_connection_suggestion,
)
from app.agents.socrates.state import SocratesState
from app.config.llm import get_analytical_llm

logger = logging.getLogger(__name__)

# 인지 왜곡 감지 설정
COGNITIVE_DISTORTION_PROMPT = """사용자의 메시지에서 인지 왜곡(cognitive distortion) 패턴을 감지하세요.

인지 왜곡 유형:
- 전부 아니면 전무 사고(all-or-nothing): "항상", "절대", "전혀"
- 과잉 일반화: 하나의 사건을 전체로 확대
- 감정적 추론: 느낌을 사실로 취급
- 자기 비난: 과도한 자책
- 파국화: 최악의 결과만 상상

메시지: {message}

JSON 형식으로 출력:
{{"detected": true/false, "type": "왜곡 유형 또는 null", "hint": "소크라테스식 반문 힌트 1문장 또는 null"}}"""

# 연결 제안 설정
CONNECTION_TURN_INTERVAL = 3


async def _detect_cognitive_distortion(message: str) -> dict:
    """사용자 메시지에서 인지 왜곡 감지. LLM 기반."""
    try:
        llm = get_analytical_llm()
        llm_with_json = llm.bind(response_format={"type": "json_object"})
        prompt = COGNITIVE_DISTORTION_PROMPT.format(message=message[:500])
        response = await llm_with_json.ainvoke([HumanMessage(content=prompt)])
        import json

        result = json.loads(response.content.strip())
        return result
    except Exception:
        logger.warning("인지 왜곡 감지 실패, 스킵")
        return {"detected": False, "type": None, "hint": None}


async def emotional_enrichment_node(state: SocratesState, runtime: Runtime[AgentContext]) -> dict:
    """감정 코칭 특화 추가 컨텍스트 수집 노드 (Socrates 에이전트 전용).

    1. formatted_memories: graded_memories를 RRF 가중 할당으로 포맷
    2. cognitive_distortion: 인지 왜곡 감지 결과를 contradiction_context로 전달
    3. connection_suggestion: 3턴 간격 연결 제안
    4. previous_session_context / topic_session_context: 첫 턴일 때만
    5. user_profile: 개인화 프로필 조회
    """
    writer = get_stream_writer()
    writer({"node": "emotional_enrichment", "status": "started"})

    user_id = state["user_id"]
    session_id = state["session_id"]
    user_query = state["user_query"]
    search_query = state.get("search_query", user_query)
    graded_memories = state.get("graded_memories", [])
    turn_count = state.get("turn_count", 0)
    source_context = state.get("source_context")

    vector_repo = runtime.context.vector_repo
    socrates_repo = runtime.context.socrates_repo

    # 1. 메모리 포맷팅
    formatted_memories = format_memories_with_budget(graded_memories, item_label="자료")

    # 2. 인지 왜곡 감지 (소크라테스식 반문 힌트 생성)
    contradiction_context = ""
    distortion_result = await _detect_cognitive_distortion(user_query)
    if distortion_result.get("detected") and distortion_result.get("hint"):
        distortion_type = distortion_result.get("type", "")
        hint = distortion_result.get("hint", "")
        contradiction_context = f"[인지 왜곡 감지: {distortion_type}]\n소크라테스식 반문 힌트: {hint}"

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
            logger.debug("연결 제안 발견: %s", title)

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

    writer({"node": "emotional_enrichment", "status": "done"})

    return {
        "formatted_memories": formatted_memories,
        "contradiction_context": contradiction_context,
        "connection_suggestion": connection_suggestion,
        "user_profile": user_profile,
        "previous_session_context": previous_session_context,
        "topic_session_context": topic_session_context,
    }
