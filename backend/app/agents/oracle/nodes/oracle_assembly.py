import logging

from langgraph.config import get_stream_writer

from app.agents.oracle.state import OracleState
from app.agents.prompts import (
    ORACLE_AGENT_PROMPT,
    build_profile_section,
    get_mode_prompt,
)
from app.agents.shared.assembly_utils import build_llm_messages, build_references
from app.agents.token_budget import enforce_context_budget

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
        ("참고 자료 (스크랩/다이어리)", formatted_memories),
        ("지식 그래프 컨텍스트", graph_context),
        ("최근 다이어리 항목", diary_context),
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


async def oracle_assembly_node(state: OracleState) -> dict:
    """Oracle 에이전트 최종 시스템 프롬프트 조립 노드.

    범용 대화 + 에이전트 전환 제안 메시지를 구성한다.
    """
    writer = get_stream_writer()
    writer({"node": "oracle_assembly", "status": "started"})

    raw_sections = {
        "formatted_memories": state.get("formatted_memories", ""),
        "graph_context": state.get("graph_context", ""),
        "contradiction_context": state.get("contradiction_context", ""),
        "diary_context": state.get("diary_context", ""),
        "community_context": state.get("community_context", ""),
        "connection_suggestion": state.get("connection_suggestion", ""),
        "previous_session_context": state.get("previous_session_context", ""),
    }
    sections = enforce_context_budget(raw_sections)

    system_prompt = _assemble_oracle_prompt(
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
    )

    if len(system_prompt) > 100_000:
        logger.warning("oracle_assembly: 시스템 프롬프트 크기 초과 (%d chars) — 절삭", len(system_prompt))
        system_prompt = system_prompt[:100_000]

    llm_messages = build_llm_messages(system_prompt, state["messages"])
    references = build_references(state.get("graded_memories", []))

    writer({"node": "oracle_assembly", "status": "done", "references": len(references)})

    return {
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "references": references,
    }
