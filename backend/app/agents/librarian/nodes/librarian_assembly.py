import logging

from langgraph.config import get_stream_writer

from app.agents.librarian.state import LibrarianChatState
from app.agents.prompts import (
    LIBRARIAN_AGENT_PROMPT,
    build_profile_section,
    get_mode_prompt,
)
from app.agents.shared.assembly_utils import build_llm_messages, build_references
from app.agents.token_budget import enforce_context_budget

logger = logging.getLogger(__name__)


def _assemble_librarian_prompt(
    mode: str | None,
    formatted_memories: str,
    graph_context: str,
    contradiction_context: str,
    user_profile: dict | None,
    connection_suggestion: str,
    source_context: dict | None,
    community_context: str,
    previous_session_context: str,
) -> str:
    """Librarian 에이전트 전용 시스템 프롬프트 조립.

    출처 인용 + 구조화된 답변 + 연결 발견 프롬프트를 조립한다.
    """
    parts = [LIBRARIAN_AGENT_PROMPT, build_profile_section(user_profile), get_mode_prompt(mode)]

    # 소스 컨텍스트 (현재 보고 있는 스크랩 정보)
    if source_context and source_context.get("type") == "scrap":
        ctx_title = source_context.get("title", "")
        ctx_preview = source_context.get("content_preview", "")
        ctx_tags = source_context.get("tags", [])
        ctx_url = source_context.get("source_url", "")

        section = "\n\n**현재 스크랩:**"
        if ctx_title:
            section += f"\n제목: {ctx_title}"
        if ctx_url:
            section += f"\n출처: {ctx_url}"
        if ctx_tags:
            section += f"\n태그: {', '.join(ctx_tags)}"
        if ctx_preview:
            section += f"\n내용 미리보기: {ctx_preview[:500]}"
        section += "\n\n이 스크랩을 중심으로 관련 지식을 탐색하세요."
        parts.append(section)

    # 커뮤니티 요약
    if community_context:
        parts.append(
            f"\n\n**사용자 지식 구조 (Knowledge Communities):**\n{community_context}\n"
            "지식 클러스터를 참고하여 연결 관계를 제안하세요."
        )

    # RAG 컨텍스트
    if formatted_memories:
        parts.append(f"\n\n**검색된 스크랩:**\n{formatted_memories}")

    if graph_context:
        parts.append(f"\n\n**지식 그래프 연결:**\n{graph_context}")

    # 모순/대비되는 지식
    if contradiction_context:
        parts.append(
            f"\n\n**대비되는 관점의 스크랩:**\n{contradiction_context}\n"
            "이 스크랩들이 어떻게 다른 관점을 제시하는지 설명하세요."
        )

    # 연결 제안
    if connection_suggestion:
        parts.append(f"\n\n**연결 제안:**\n다음 스크랩이 현재 주제와 연결될 수 있습니다:\n{connection_suggestion}")

    # 이전 세션 컨텍스트
    if previous_session_context:
        parts.append(previous_session_context)

    return "".join(parts)


async def librarian_assembly_node(state: LibrarianChatState) -> dict:
    """Librarian 에이전트 최종 시스템 프롬프트 조립 노드.

    출처 인용 + 구조화 답변 + 스크랩 간 연결 발견에 특화된 프롬프트를 구성한다.
    """
    writer = get_stream_writer()
    writer({"node": "librarian_assembly", "status": "started"})

    raw_sections = {
        "formatted_memories": state.get("formatted_memories", ""),
        "graph_context": state.get("graph_context", ""),
        "contradiction_context": state.get("contradiction_context", ""),
        "community_context": state.get("community_context", ""),
        "connection_suggestion": state.get("connection_suggestion", ""),
        "previous_session_context": state.get("previous_session_context", ""),
    }
    sections = enforce_context_budget(raw_sections)

    system_prompt = _assemble_librarian_prompt(
        mode=state.get("detected_mode"),
        formatted_memories=sections["formatted_memories"],
        graph_context=sections["graph_context"],
        contradiction_context=sections["contradiction_context"],
        user_profile=state.get("user_profile"),
        connection_suggestion=sections["connection_suggestion"],
        source_context=state.get("source_context"),
        community_context=sections["community_context"],
        previous_session_context=sections["previous_session_context"],
    )

    if len(system_prompt) > 100_000:
        logger.warning("librarian_assembly: 시스템 프롬프트 크기 초과 (%d chars) — 절삭", len(system_prompt))
        system_prompt = system_prompt[:100_000]

    llm_messages = build_llm_messages(system_prompt, state["messages"])
    references = build_references(state.get("graded_memories", []))

    writer({"node": "librarian_assembly", "status": "done", "references": len(references)})

    return {
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "references": references,
    }
