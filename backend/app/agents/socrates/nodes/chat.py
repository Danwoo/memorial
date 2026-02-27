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
from app.config.llm import get_analytical_llm, get_streaming_llm
from app.repositories.diary_repository import DiaryRepository
from app.repositories.vector_repository import VectorRepository
from app.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)

# RAG 컨텍스트 검색 설정
VECTOR_SEARCH_LIMIT = 5
VECTOR_SEARCH_THRESHOLD = 0.5
GRAPH_CONTEXT_LIMIT = 8
GRAPH_KEYWORD_MIN_LENGTH = 2
GRAPH_MAX_KEYWORDS = 3
JOURNAL_CONTEXT_LIMIT = 3
JOURNAL_PREVIEW_LENGTH = 400
# 반론 검색 설정
CONTRADICTION_SEARCH_LIMIT = 2
CONTRADICTION_THRESHOLD = 0.4
MAX_CONTRADICTING_RESULTS = 3
# 컨텍스트 예산 (가변 길이 할당)
CONTEXT_BUDGET_CHARS = 4000
# dense 검색 임계값 (0.25 이하는 실질적 무관)
DENSE_THRESHOLD = 0.25
# 연결 제안 설정
CONNECTION_SUGGEST_LOW = 0.80
CONNECTION_SUGGEST_HIGH = 0.92
CONNECTION_TURN_INTERVAL = 3

# 의도 자동 분류 키워드
_COUNTER_KEYWORDS = ["반론", "반대", "비판", "다른 관점", "약점", "문제점", "단점", "criticism"]
_SUMMARY_KEYWORDS = ["요약", "정리", "핵심", "줄여", "summarize"]
_EVENING_KEYWORDS = ["하루 정리", "하루 돌아", "오늘 회고", "저녁 회고", "하루를 마무리"]
_INSIGHT_KEYWORDS = ["깊이 생각", "분석해", "본질", "통찰"]
_ASSUMPTION_KEYWORDS = ["전제", "가정", "전제 분석", "assumption", "숨겨진 가정"]
_FIVE_WHYS_KEYWORDS = ["왜 그런", "근본 원인", "왜?", "5 whys", "파고들"]
_DIALECTIC_KEYWORDS = ["비교", "뭐가 나을", "장단점", "vs", "선택지", "어떤 게 좋"]

QUERY_REWRITE_PROMPT = """You are a search query optimizer for a personal knowledge management system.

Given a conversation history and the user's latest message, rewrite the message into
a standalone search query that captures the user's actual information need.

Rules:
1. Resolve pronouns and references ("that", "it", "the one I mentioned", "그거", "아까")
   using conversation context
2. If the message is already a clear, self-contained query, return it unchanged
3. For comparison requests ("compare X and Y"), output TWO queries separated by |||
4. Keep the query in the same language as the user's message
5. Output ONLY the rewritten query, nothing else

Example 1:
History: User asked about React hooks. AI explained useState.
Latest: "What about the other one?"
Output: React useEffect hook

Example 2:
History: User discussed pros of functional programming
Latest: "그거랑 OOP 비교해줘"
Output: 함수형 프로그래밍 장점 ||| 객체지향 프로그래밍 장점

Example 3:
Latest: "함수형 프로그래밍의 장점은?"
Output: 함수형 프로그래밍의 장점"""

BATCH_RELEVANCE_PROMPT = """Rate the relevance of each memory to the query.
For each memory, output its number followed by "yes" or "no".
A memory is relevant if it directly addresses the query topic, provides useful context, or contains information that helps explore the query.

Query: {query}

{numbered_memories}

Output format (one per line):
1: yes
2: no
..."""


def detect_intent(message: str) -> str | None:
    """사용자 메시지에서 대화 의도를 키워드 기반으로 자동 분류.

    반환값은 mode 문자열(insight/counter/summary/evening/assumption/five_whys/dialectic) 또는 None(기본).
    """
    msg = message.lower()
    for keywords, mode_value in [
        (_COUNTER_KEYWORDS, "counter"),
        (_SUMMARY_KEYWORDS, "summary"),
        (_EVENING_KEYWORDS, "evening"),
        (_INSIGHT_KEYWORDS, "insight"),
        (_ASSUMPTION_KEYWORDS, "assumption"),
        (_FIVE_WHYS_KEYWORDS, "five_whys"),
        (_DIALECTIC_KEYWORDS, "dialectic"),
    ]:
        if any(kw in msg for kw in keywords):
            return mode_value
    return None


async def _rewrite_query(messages: list[BaseMessage], query: str) -> list[str]:
    """대화 맥락 반영 쿼리 재작성. 복합 질의는 분해."""
    if len(messages) <= 1:
        return [query]

    recent = messages[-6:]
    history = "\n".join(f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content[:200]}" for m in recent[:-1])
    try:
        llm = get_analytical_llm()
        response = await llm.ainvoke(
            [
                SystemMessage(content=QUERY_REWRITE_PROMPT),
                HumanMessage(content=f"History:\n{history}\n\nLatest: {query}"),
            ]
        )
        queries = [q.strip() for q in response.content.strip().split("|||") if q.strip()]
        return queries if queries else [query]
    except Exception:
        logger.warning("Query rewrite 실패, 원본 사용")
        return [query]


async def _grade_relevance(query: str, memories: list[dict]) -> list[dict]:
    """검색된 기억들의 관련성을 LLM으로 평가. 배치 처리로 1회 호출."""
    if not memories:
        return []
    try:
        numbered_lines = []
        for i, mem in enumerate(memories, 1):
            date = mem.get("created_at", "")[:10]
            title = mem.get("title", "Untitled")
            summary = mem.get("summary") or mem.get("content", "")[:300]
            numbered_lines.append(f"{i}. [{date}] {title} — {summary[:200]}")

        prompt_text = BATCH_RELEVANCE_PROMPT.format(
            query=query,
            numbered_memories="\n".join(numbered_lines),
        )
        llm = get_analytical_llm()
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        output = response.content.strip()

        graded = []
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                try:
                    idx = int(parts[0].strip()) - 1
                    verdict = parts[1].strip().lower()
                    if 0 <= idx < len(memories) and "yes" in verdict:
                        graded.append(memories[idx])
                except (ValueError, IndexError):
                    pass
        return graded
    except Exception:
        logger.warning("Relevance grading 실패, 전체 반환")
        return memories


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
        f"{query} 단점",
        f"{query} 비판",
        f"{query} 한계",
        f"{query} 반대 의견",
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
            dense_threshold=DENSE_THRESHOLD,
        )

        if results:
            # 관련성 grading
            graded = await _grade_relevance(query, results)
            if not graded:
                # fallback: 임계값 낮춰서 재검색
                logger.debug("관련 기억 없음, 임계값 0.0으로 재검색")
                results = await hybrid_search.search(
                    user_id=UUID(user_id),
                    query=query,
                    limit=limit,
                    dense_threshold=0.0,
                )
                graded = results  # 재검색 결과는 그대로 사용

            formatted = _format_memories_with_budget(graded)
            return formatted, graded
    except Exception:
        logger.exception("Hybrid search failed")
    return "", []


def _format_memories_with_budget(memories: list[dict], budget: int = CONTEXT_BUDGET_CHARS) -> str:
    """RRF 순위 기반 가변 길이 할당. 상위 결과에 더 많은 컨텍스트."""
    if not memories:
        return ""
    n = len(memories)
    weights = [1.0 / (i + 1) for i in range(n)]
    total_w = sum(weights)
    allocs = [int(budget * w / total_w) for w in weights]

    lines = []
    for i, mem in enumerate(memories):
        date = mem.get("created_at", "")[:10]
        title = mem.get("title", "Untitled")
        tags = ", ".join(mem.get("tags", []) or [])
        content = mem.get("summary") or mem.get("content", "")
        alloc = allocs[i] if i < len(allocs) else 200
        preview = content[:alloc]

        header = f"--- 기억 #{i + 1} [{date}] {title} ---"
        if tags:
            header += f"\n태그: {tags}"
        lines.append(f"{header}\n{preview}")
    return "\n\n".join(lines)


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
        from app.config.dependencies import get_mindmap_repository

        graph_repo = get_mindmap_repository()

        keywords = [word for word in query.split() if len(word) >= GRAPH_KEYWORD_MIN_LENGTH][:GRAPH_MAX_KEYWORDS]
        graph_results = []
        for keyword in keywords:
            related = await graph_repo.get_related_context(keyword, depth=2)
            graph_results.extend(related)

        if not graph_results:
            return ""

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


async def _fetch_diary_context(
    user_id: str | UUID,
    diary_repo: DiaryRepository,
    limit: int = JOURNAL_CONTEXT_LIMIT,
) -> str:
    """최근 다이어리 항목 조회. 포맷된 텍스트 반환."""
    try:
        recent_diaries = await diary_repo.get_diaries(user_id, limit=limit)
        if recent_diaries:
            return "\n".join(
                f"- [Diary {diary.get('created_at', '')[:10]}] "
                f"Mood: {diary.get('mood', 'N/A')} | "
                f"Tags: {', '.join(diary.get('tags', []) or [])} — "
                f"{diary.get('content', '')[:JOURNAL_PREVIEW_LENGTH]}..."
                for diary in recent_diaries
            )
    except Exception:
        logger.exception("Diary context fetch failed")
    return ""


async def _get_community_context(user_id: str, query: str) -> str:
    """커뮤니티 요약 중 쿼리와 관련된 것만 필터링하여 반환."""
    try:
        container = get_agent_container()
        summaries = await container.community_summary.get_community_summaries(user_id)
        if not summaries:
            return ""

        query_keywords = {word.lower() for word in query.split() if len(word) >= 2}
        relevant = []
        for s in summaries:
            entity_words = {e.lower() for e in s.get("entities", [])}
            # 쿼리 키워드와 엔티티가 겹치면 관련 있음
            if query_keywords & entity_words:
                relevant.append(s["summary"])

        # 관련 없으면 상위 2개 일반 커뮤니티 제공
        if not relevant:
            relevant = [s["summary"] for s in summaries[:2]]

        return "\n".join(f"- {s}" for s in relevant[:3])
    except Exception:
        logger.warning("Community context fetch 실패")
        return ""


async def prepare_socrates_context(
    messages: list[BaseMessage],
    mode: str | None = None,
    user_id: str | None = None,
    turn_count: int = 0,
    source_context: dict | None = None,
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
    community_context = ""
    current_memories: list = []

    last_message = messages[-1] if messages else None
    if isinstance(last_message, HumanMessage):
        query = last_message.content
        container = get_agent_container()

        # mode가 명시적으로 전달되지 않으면 메시지에서 자동 분류
        if not mode:
            mode = detect_intent(query)

        # 쿼리 재작성 (대명사 해소, 복합 쿼리 분해)
        rewritten_queries = await _rewrite_query(messages, query)
        search_query = rewritten_queries[0]
        logger.debug("쿼리 재작성: %r → %r", query[:50], search_query[:50])

        # 다중 쿼리 검색 (복합 질의 분해 시)
        if len(rewritten_queries) > 1:
            all_results = []
            seen_ids: set[str] = set()
            for rq in rewritten_queries:
                _, results = await _search_hybrid_memories(rq, container.hybrid_search, user_id=user_id)
                for r in results:
                    rid = r.get("id", "")
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        all_results.append(r)
            current_memories = all_results[:VECTOR_SEARCH_LIMIT]
            context_memories = _format_memories_with_budget(current_memories)
        else:
            context_memories, current_memories = await _search_hybrid_memories(
                search_query,
                container.hybrid_search,
                user_id=user_id,
            )
        logger.debug("RAG 하이브리드 검색 결과: query=%s, memories=%d개", search_query[:50], len(current_memories))

        graph_context = await _fetch_graph_context(search_query)

        if user_id:
            journal_context = await _fetch_diary_context(user_id, container.diary_repo)
            community_context = await _get_community_context(user_id, search_query)

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
                summary = suggestion.get("summary") or suggestion.get("content", "")[:200]
                connection_context = f"[{date}] {title}: {summary}"
                logger.debug("연결 제안 발견: %s", title)

    # 사용자 프로필 조회 (개인화된 프롬프트)
    from app.services.user_profile_service import get_user_profile

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
        source_context,
        community_context,
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
            return "\n".join(
                f"- [{m.get('created_at', '')[:10]}] {m.get('title', 'Untitled')}: "
                f"{(m.get('summary') or m.get('content', ''))[:200]}"
                for m in contradicting
            )
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
    source_context: dict | None = None,
    community_context: str = "",
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
            greeting = "오늘 하루 어떠셨나요? 오늘 저장한 내용들을 함께 돌아볼까요?"
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
