import logging

from langchain_core.messages import SystemMessage
from langgraph.config import get_stream_writer

from app.agents.prompts import (
    SOCRATES_BASE_PROMPT,
    build_profile_section,
    get_mode_prompt,
)
from app.agents.socrates.state import SocratesState

logger = logging.getLogger(__name__)


def _assemble_system_prompt(
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
    """시스템 프롬프트에 RAG 컨텍스트 + 사용자 프로필 섹션을 조합."""
    parts = [SOCRATES_BASE_PROMPT, build_profile_section(user_profile), get_mode_prompt(mode)]

    # 소스 컨텍스트 (현재 작업 화면 정보)
    if source_context:
        ctx_type = source_context.get("type", "")
        ctx_title = source_context.get("title", "")
        ctx_preview = source_context.get("content_preview", "")
        ctx_tags = source_context.get("tags", [])
        ctx_neighbors = source_context.get("graph_neighbors", [])

        section = f"\n\n**현재 사용자 컨텍스트 ({ctx_type}):**"
        if ctx_title:
            section += f"\n제목: {ctx_title}"
        if ctx_preview:
            section += f"\n내용 미리보기: {ctx_preview[:500]}"
        if ctx_tags:
            section += f"\n태그: {', '.join(ctx_tags)}"
        if ctx_neighbors:
            neighbor_lines = [f"- {n['name']} ({n['label']}) -- {n['relation_type']}" for n in ctx_neighbors[:10]]
            section += "\n연결된 노드:\n" + "\n".join(neighbor_lines)
        section += "\n\n이 맥락을 활용하여 사용자의 현재 작업과 연결된 대화를 진행하세요."
        parts.append(section)

    # 커뮤니티 요약 (거시적 지식 구조)
    if community_context:
        parts.append(
            f"\n\n**사용자 지식 구조 (Knowledge Communities):**\n{community_context}\n"
            "이 지식 구조를 참고하여 사용자의 관심사 간 연결을 제안하세요."
        )

    context_sections = [
        ("검색된 기억", formatted_memories),
        ("지식 그래프 컨텍스트", graph_context),
        ("반대 의견 기억", contradiction_context),
        ("최근 저널 항목", diary_context),
    ]
    for title, content in context_sections:
        if content:
            parts.append(f"\n\n**{title}:**\n{content}")

    if connection_suggestion:
        parts.append(
            f"\n\n**연결 제안 (자연스럽게 대화에 녹여서 언급하세요):**\n"
            f"다음 기억이 현재 대화와 관련될 수 있습니다. 적절한 타이밍에 "
            f"'예전에 저장하신 내용 중...' 형태로 자연스럽게 연결해주세요:\n"
            f"{connection_suggestion}"
        )

    # 이전 세션 / 주제 세션 컨텍스트
    if previous_session_context:
        parts.append(previous_session_context)
    if topic_session_context:
        parts.append(topic_session_context)

    return "".join(parts)


async def context_assembly_node(state: SocratesState) -> dict:
    """최종 시스템 프롬프트 조립 + LLM 메시지 구성 노드.

    enrichment까지 수집된 모든 컨텍스트를 조합하여 시스템 프롬프트를 생성하고
    LLM 호출용 메시지 리스트를 반환한다. 외부 DI/retry 불필요.
    """
    writer = get_stream_writer()
    writer({"node": "context_assembly", "status": "started"})

    system_prompt = _assemble_system_prompt(
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
        topic_session_context=state.get("topic_session_context", ""),
    )

    messages = state["messages"]
    llm_messages = [SystemMessage(content=system_prompt), *messages]

    # 참조 메모리 (최대 5개, 프론트엔드용 포맷)
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

    writer(
        {
            "node": "context_assembly",
            "status": "done",
            "references": len(references),
        }
    )

    return {
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "references": references,
    }
