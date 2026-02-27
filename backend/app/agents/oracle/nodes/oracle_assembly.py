import logging

from langchain_core.messages import SystemMessage
from langgraph.config import get_stream_writer

from app.agents.prompts import (
    ORACLE_AGENT_PROMPT,
    build_profile_section,
    get_mode_prompt,
)
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)


def _assemble_oracle_prompt(
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
) -> str:
    """Oracle 에이전트 시스템 프롬프트 조립.

    범용 대화 + 에이전트 전환 제안 기능을 포함한다.
    """
    parts = [ORACLE_AGENT_PROMPT, build_profile_section(user_profile), get_mode_prompt(mode)]

    # 소스 컨텍스트
    if source_context:
        ctx_type = source_context.get("type", "")
        ctx_title = source_context.get("title", "")
        ctx_preview = source_context.get("content_preview", "")
        ctx_tags = source_context.get("tags", [])

        section = f"\n\n**현재 사용자 컨텍스트 ({ctx_type}):**"
        if ctx_title:
            section += f"\n제목: {ctx_title}"
        if ctx_preview:
            section += f"\n내용 미리보기: {ctx_preview[:500]}"
        if ctx_tags:
            section += f"\n태그: {', '.join(ctx_tags)}"
        parts.append(section)

    # 커뮤니티 요약
    if community_context:
        parts.append(f"\n\n**사용자 지식 구조:**\n{community_context}")

    # RAG 컨텍스트
    context_sections = [
        ("검색된 기억", formatted_memories),
        ("지식 그래프 컨텍스트", graph_context),
        ("최근 저널 항목", diary_context),
    ]
    for title, content in context_sections:
        if content:
            parts.append(f"\n\n**{title}:**\n{content}")

    # 에이전트 전환 제안 (contradiction_context 필드 재활용)
    if contradiction_context:
        parts.append(f"\n\n**참고:**\n{contradiction_context}")

    # 연결 제안
    if connection_suggestion:
        parts.append(f"\n\n**연결 제안:**\n다음 기억이 현재 대화와 관련될 수 있습니다:\n{connection_suggestion}")

    # 이전 세션 컨텍스트
    if previous_session_context:
        parts.append(previous_session_context)

    return "".join(parts)


async def oracle_assembly_node(state: SocratesState) -> dict:
    """Oracle 에이전트 최종 시스템 프롬프트 조립 노드.

    범용 대화 + 에이전트 전환 제안 메시지를 구성한다.
    """
    writer = get_stream_writer()
    writer({"node": "oracle_assembly", "status": "started"})

    system_prompt = _assemble_oracle_prompt(
        mode=state.get("detected_mode"),
        formatted_memories=state.get("formatted_memories", ""),
        graph_context=state.get("graph_context", ""),
        contradiction_context=state.get("contradiction_context", ""),
        diary_context=state.get("diary_context", ""),
        user_profile=state.get("user_profile"),
        connection_suggestion=state.get("connection_suggestion", ""),
        source_context=state.get("source_context"),
        community_context=state.get("community_context", ""),
        previous_session_context=state.get("previous_session_context", ""),
    )

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

    writer({"node": "oracle_assembly", "status": "done", "references": len(references)})

    return {
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "references": references,
    }
