import logging

from langchain_core.messages import SystemMessage
from langgraph.config import get_stream_writer

from app.agents.prompts import (
    SOCRATES_AGENT_PROMPT,
    build_profile_section,
    get_mode_prompt,
)
from app.agents.socrates.state import SocratesState
from app.agents.token_budget import enforce_context_budget

logger = logging.getLogger(__name__)


def _assemble_socrates_prompt(
    mode: str | None,
    formatted_memories: str,
    graph_context: str,
    contradiction_context: str,
    diary_context: str,
    user_profile: dict | None,
    connection_suggestion: str,
    source_context: dict | None,
    community_context: str,
    previous_session_context: str,
    topic_session_context: str,
) -> str:
    """Socrates 에이전트 전용 시스템 프롬프트 조립.

    공감 → 탐색질문 → 인사이트 순서로 구성되며 감정 코칭에 특화된 프롬프트를 사용한다.
    """
    parts = [SOCRATES_AGENT_PROMPT, build_profile_section(user_profile), get_mode_prompt(mode)]

    # 현재 다이어리 컨텍스트 (diary_deep_retrieval에서 제공)
    if diary_context:
        parts.append(f"\n\n{diary_context}")

    # 커뮤니티 요약
    if community_context:
        parts.append(
            f"\n\n**사용자 지식 구조 (Knowledge Communities):**\n{community_context}\n"
            "이 지식 구조를 참고하여 사용자의 관심사 간 연결을 제안하세요."
        )

    # RAG 컨텍스트 섹션
    context_sections = [
        ("검색된 기억", formatted_memories),
        ("지식 그래프 컨텍스트", graph_context),
    ]
    for title, content in context_sections:
        if content:
            parts.append(f"\n\n**{title}:**\n{content}")

    # 인지 왜곡 탐지 결과
    if contradiction_context:
        parts.append(
            f"\n\n**감정 패턴 분석:**\n{contradiction_context}\n"
            "이 패턴을 부드럽게 탐색하되, 직접 지적하지 말고 소크라테스식 질문으로 접근하세요."
        )

    # 연결 제안
    if connection_suggestion:
        parts.append(
            f"\n\n**연결 제안 (자연스럽게 대화에 녹여서 언급하세요):**\n"
            f"다음 기억이 현재 대화와 관련될 수 있습니다:\n{connection_suggestion}"
        )

    # 이전 세션 / 주제 세션 컨텍스트
    if previous_session_context:
        parts.append(previous_session_context)
    if topic_session_context:
        parts.append(topic_session_context)

    return "".join(parts)


async def socrates_assembly_node(state: SocratesState) -> dict:
    """Socrates 에이전트 최종 시스템 프롬프트 조립 노드.

    공감 → 탐색질문 → 인사이트 순서 프롬프트로 감정 코칭에 특화된 메시지를 구성한다.
    """
    writer = get_stream_writer()
    writer({"node": "socrates_assembly", "status": "started"})

    raw_sections = {
        "formatted_memories": state.get("formatted_memories", ""),
        "graph_context": state.get("graph_context", ""),
        "contradiction_context": state.get("contradiction_context", ""),
        "diary_context": state.get("diary_context", ""),
        "community_context": state.get("community_context", ""),
        "connection_suggestion": state.get("connection_suggestion", ""),
        "previous_session_context": state.get("previous_session_context", ""),
        "topic_session_context": state.get("topic_session_context", ""),
    }
    sections = enforce_context_budget(raw_sections)

    system_prompt = _assemble_socrates_prompt(
        mode=state.get("detected_mode"),
        formatted_memories=sections["formatted_memories"],
        graph_context=sections["graph_context"],
        contradiction_context=sections["contradiction_context"],
        diary_context=sections["diary_context"],
        user_profile=state.get("user_profile"),
        connection_suggestion=sections["connection_suggestion"],
        source_context=state.get("source_context"),
        community_context=sections["community_context"],
        previous_session_context=sections["previous_session_context"],
        topic_session_context=sections["topic_session_context"],
    )

    if len(system_prompt) > 100_000:
        logger.warning("socrates_assembly: 시스템 프롬프트 크기 초과 (%d chars) — 절삭", len(system_prompt))
        system_prompt = system_prompt[:100_000]

    messages = state["messages"]
    llm_messages = [SystemMessage(content=system_prompt), *messages]

    graded_memories = state.get("graded_memories", [])
    references = [
        {
            "id": str(m.get("id", "")),
            "title": m.get("title", ""),
            "source_type": m.get("source_type", "NOTE"),
            "created_at": str(m.get("created_at", ""))[:10],
        }
        for m in graded_memories[:5]
    ]

    writer({"node": "socrates_assembly", "status": "done", "references": len(references)})

    return {
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "references": references,
    }
