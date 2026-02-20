import logging
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.container import get_agent_container
from app.agents.prompts import (
    SOCRATES_BASE_PROMPT,
    build_profile_section,
    get_mode_prompt,
)
from app.agents.state import AgentState
from app.config.llm import get_streaming_llm
from app.repositories.journal_repository import JournalRepository
from app.repositories.vector_repository import VectorRepository
from app.services.hybrid_search_service import HybridSearchService
from app.services.user_profile_service import get_user_profile

logger = logging.getLogger(__name__)

# RAG 컨텍스트 검색 설정
VECTOR_SEARCH_LIMIT = 5
VECTOR_SEARCH_THRESHOLD = 0.5
GRAPH_CONTEXT_LIMIT = 8
GRAPH_KEYWORD_MIN_LENGTH = 3
GRAPH_MAX_KEYWORDS = 3
JOURNAL_CONTEXT_LIMIT = 3
JOURNAL_PREVIEW_LENGTH = 80
# 반론 검색 설정
CONTRADICTION_SEARCH_LIMIT = 2
CONTRADICTION_THRESHOLD = 0.4
MAX_CONTRADICTING_RESULTS = 3
# 메모리 미리보기 길이
MEMORY_CONTEXT_PREVIEW_LENGTH = 100
# 연결 제안 설정
CONNECTION_SUGGEST_LOW = 0.80
CONNECTION_SUGGEST_HIGH = 0.92
CONNECTION_TURN_INTERVAL = 3

# 의도 자동 분류 키워드
_COUNTER_KEYWORDS = ["반론", "반대", "비판", "다른 관점", "약점", "문제점", "단점", "criticism"]
_SUMMARY_KEYWORDS = ["요약", "정리", "핵심", "줄여", "summarize"]
_EVENING_KEYWORDS = ["하루 정리", "하루 돌아", "오늘 회고", "저녁 회고", "하루를 마무리"]
_INSIGHT_KEYWORDS = ["깊이 생각", "분석해", "왜 그런", "근본 원인", "본질", "통찰"]


def detect_intent(message: str) -> str | None:
    """사용자 메시지에서 대화 의도를 키워드 기반으로 자동 분류.

    반환값은 mode 문자열(insight/counter/summary/evening) 또는 None(기본).
    """
    msg = message.lower()
    for keywords, mode_value in [
        (_COUNTER_KEYWORDS, "counter"),
        (_SUMMARY_KEYWORDS, "summary"),
        (_EVENING_KEYWORDS, "evening"),
        (_INSIGHT_KEYWORDS, "insight"),
    ]:
        if any(kw in msg for kw in keywords):
            return mode_value
    return None


async def find_contradicting_memories(
    query: str,
    current_memories: list,
    user_id: str | None = None,
    vector_repo: VectorRepository | None = None,
) -> list:
    """현재 주제와 반대되는 메모리를 벡터 검색으로 탐색."""
    if not vector_repo:
        vector_repo = get_agent_container().vector_repo
    filters = {"user_id": str(user_id)} if user_id else {}

    contradiction_queries = [
        f"disadvantages of {query}",
        f"problems with {query}",
        f"criticism of {query}",
        f"opposite of {query}",
    ]

    current_ids = {m.get("id") for m in current_memories}
    contradicting = []
    for cq in contradiction_queries[:CONTRADICTION_SEARCH_LIMIT]:
        try:
            results = await vector_repo.similarity_search(
                cq,
                limit=CONTRADICTION_SEARCH_LIMIT,
                threshold=CONTRADICTION_THRESHOLD,
                filters=filters,
            )
            for r in results:
                if r.get("id") not in current_ids:
                    contradicting.append(r)
        except Exception:
            pass

    return contradicting[:MAX_CONTRADICTING_RESULTS]


async def _search_hybrid_memories(
    query: str,
    hybrid_search: HybridSearchService,
    limit: int = VECTOR_SEARCH_LIMIT,
    user_id: str | None = None,
) -> tuple[str, list]:
    """하이브리드 검색 (Dense + Sparse + Graph). (포맷된 텍스트, 원본 결과) 반환."""
    try:
        if not user_id:
            return "", []

        results = await hybrid_search.search(
            user_id=UUID(user_id),
            query=query,
            limit=limit,
            dense_threshold=0.0,
        )
        if results:
            formatted = "\n\n".join(_format_memory_line(memory, index=i + 1) for i, memory in enumerate(results))
            return formatted, results
    except Exception:
        logger.exception("Hybrid search failed")
    return "", []


def _format_memory_line(memory: dict, index: int | None = None) -> str:
    """메모리 항목을 블록 구분자 포함 컨텍스트 문자열로 포맷."""
    date = memory.get("created_at", "")[:10]
    title = memory.get("title", "Untitled")
    summary = memory.get("summary") or memory.get("content", "")[:MEMORY_CONTEXT_PREVIEW_LENGTH]
    if index is not None:
        return f"--- 기억 #{index} ---\n[{date}] {title}\n{summary}"
    return f"- [{date}] {title}: {summary}"


async def _search_connection_suggestions(
    query: str,
    vector_repo: VectorRepository,
    already_referenced_ids: set,
    user_id: str | None = None,
) -> dict | None:
    """0.80~0.92 유사도 범위에서 이미 참조된 ID를 제외하고 1개 연결 후보 반환."""
    try:
        filters = {"user_id": str(user_id)} if user_id else {}
        results = await vector_repo.similarity_search(
            query,
            limit=5,
            threshold=CONNECTION_SUGGEST_LOW,
            filters=filters,
        )
        for r in results:
            sim = r.get("similarity", 0)
            if CONNECTION_SUGGEST_LOW <= sim <= CONNECTION_SUGGEST_HIGH and r.get("id") not in already_referenced_ids:
                return r
    except Exception:
        logger.exception("Connection suggestion search failed")
    return None


async def _fetch_graph_context(query: str, limit: int = GRAPH_CONTEXT_LIMIT) -> str:
    """지식 그래프에서 관련 엔티티 조회. 포맷된 텍스트 반환."""
    try:
        from app.config.dependencies import get_graph_repository

        graph_repo = get_graph_repository()

        keywords = [word for word in query.split() if len(word) > GRAPH_KEYWORD_MIN_LENGTH][:GRAPH_MAX_KEYWORDS]
        graph_results = []
        for keyword in keywords:
            related = await graph_repo.get_related_context(keyword, depth=2)
            graph_results.extend(related)

        if not graph_results:
            return ""

        # 이름 기준 중복 제거
        seen: set[str] = set()
        unique_results = []
        for entity in graph_results:
            name = entity.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_results.append(entity)

        graph_lines = []
        for entity in unique_results[:limit]:
            name = entity.get("name", "")
            label = entity.get("label", "")
            rel = entity.get("rel_type", "RELATED_TO")
            dist = entity.get("distance", 1)
            graph_lines.append(f"- {name} ({label}) -- {rel} (depth: {dist})")
        return "\n".join(graph_lines)
    except Exception:
        logger.exception("Graph context fetch failed")
        return ""


async def _fetch_journal_context(
    user_id: str | UUID,
    journal_repo: JournalRepository,
    limit: int = JOURNAL_CONTEXT_LIMIT,
) -> str:
    """최근 저널 항목 조회. 포맷된 텍스트 반환."""
    try:
        recent_journals = await journal_repo.get_journals(user_id, limit=limit)
        if recent_journals:
            return "\n".join(
                f"- [Journal {journal.get('created_at', '')[:10]}] "
                f"Mood: {journal.get('mood', 'N/A')} - "
                f"{journal.get('content', '')[:JOURNAL_PREVIEW_LENGTH]}..."
                for journal in recent_journals
            )
    except Exception:
        logger.exception("Journal context fetch failed")
    return ""


async def prepare_socrates_context(
    messages: list[BaseMessage],
    mode: str | None = None,
    user_id: str | None = None,
    turn_count: int = 0,
) -> tuple[list[BaseMessage], list[dict]]:
    """Socrates용 RAG 컨텍스트가 포함된 LangChain 메시지 리스트 준비.

    벡터 검색, 저널 조회, 모드별 프롬프트를 결합하여
    LLM 호출에 바로 사용할 수 있는 (메시지 리스트, 참조 메모리) 튜플을 반환한다.
    """
    context_memories = ""
    contradicting_memories = ""
    graph_context = ""
    journal_context = ""
    connection_context = ""
    current_memories: list = []

    last_message = messages[-1] if messages else None
    if isinstance(last_message, HumanMessage):
        query = last_message.content
        container = get_agent_container()

        # mode가 명시적으로 전달되지 않으면 메시지에서 자동 분류
        if not mode:
            mode = detect_intent(query)

        context_memories, current_memories = await _search_hybrid_memories(
            query,
            container.hybrid_search,
            user_id=user_id,
        )
        logger.debug("RAG 하이브리드 검색 결과: query=%s, memories=%d개", query[:50], len(current_memories))
        graph_context = await _fetch_graph_context(query)

        if user_id:
            journal_context = await _fetch_journal_context(user_id, container.journal_repo)

        if mode == "counter" and current_memories:
            contradicting_memories = await _build_contradiction_context(
                query, current_memories, user_id, container.vector_repo
            )

        # 3턴 간격으로 연결 제안 검색
        if turn_count > 0 and turn_count % CONNECTION_TURN_INTERVAL == 0:
            referenced_ids = {m.get("id") for m in current_memories}
            suggestion = await _search_connection_suggestions(query, container.vector_repo, referenced_ids, user_id)
            if suggestion:
                date = suggestion.get("created_at", "")[:10]
                title = suggestion.get("title", "Untitled")
                summary = suggestion.get("summary") or suggestion.get("content", "")[:MEMORY_CONTEXT_PREVIEW_LENGTH]
                connection_context = f"[{date}] {title}: {summary}"
                logger.debug("연결 제안 발견: %s", title)

    # 사용자 프로필 조회 (개인화된 프롬프트)
    user_profile = None
    if user_id:
        user_profile = await get_user_profile(user_id)

    system_content = _assemble_system_prompt(
        mode,
        context_memories,
        graph_context,
        contradicting_memories,
        journal_context,
        user_profile,
        connection_context,
    )

    return [SystemMessage(content=system_content), *messages], current_memories


async def _build_contradiction_context(
    query: str,
    current_memories: list,
    user_id: str | None = None,
    vector_repo: VectorRepository | None = None,
) -> str:
    """반론 검색 후 포맷된 컨텍스트 문자열 반환."""
    try:
        contradicting = await find_contradicting_memories(query, current_memories, user_id, vector_repo)
        if contradicting:
            return "\n".join(_format_memory_line(memory) for memory in contradicting)
    except Exception:
        logger.exception("Contradiction search failed")
    return ""


def _assemble_system_prompt(
    mode: str | None,
    context_memories: str,
    graph_context: str,
    contradicting_memories: str,
    journal_context: str,
    user_profile: dict | None = None,
    connection_context: str = "",
) -> str:
    """시스템 프롬프트에 RAG 컨텍스트 + 사용자 프로필 섹션을 조합."""
    parts = [SOCRATES_BASE_PROMPT, build_profile_section(user_profile), get_mode_prompt(mode)]

    context_sections = [
        ("검색된 기억", context_memories),
        ("지식 그래프 컨텍스트", graph_context),
        ("반대 의견 기억", contradicting_memories),
        ("최근 저널 항목", journal_context),
    ]
    for title, content in context_sections:
        if content:
            parts.append(f"\n\n**{title}:**\n{content}")

    if connection_context:
        parts.append(
            f"\n\n**연결 제안 (자연스럽게 대화에 녹여서 언급하세요):**\n"
            f"다음 기억이 현재 대화와 관련될 수 있습니다. 적절한 타이밍에 "
            f"'예전에 저장하신 내용 중...' 형태로 자연스럽게 연결해주세요:\n"
            f"{connection_context}"
        )

    return "".join(parts)


async def socrates_node(state: AgentState) -> dict:
    """Socrates 노드: 다중 대화 모드를 지원하는 소크라테스 대화 처리.

    Args:
        state: messages(대화 이력), context.mode(insight/counter/summary/evening)를 포함한 상태

    Returns:
        AI 응답이 추가된 messages를 포함한 dict
    """
    messages = state.get("messages", [])
    context = state.get("context", {})
    mode = context.get("mode") if isinstance(context, dict) else None

    if not messages:
        greeting = "안녕하세요! 무엇을 도와드릴까요?"
        if mode == "evening":
            greeting = "🌙 오늘 하루 어떠셨나요? 오늘 저장한 내용들을 함께 돌아볼까요?"
        return {"messages": [AIMessage(content=greeting)], "next_step": "end"}

    user_id = state.get("user_id")
    lc_messages, _refs = await prepare_socrates_context(messages, mode, user_id=user_id)
    llm = get_streaming_llm()

    try:
        response = await llm.ainvoke(lc_messages)
        return {"messages": [response], "next_step": "end"}
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"죄송합니다, 오류가 발생했습니다: {str(e)}")],
            "next_step": "end",
            "error": str(e),
        }
