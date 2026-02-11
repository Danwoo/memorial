import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_streaming_llm

logger = logging.getLogger(__name__)

# 기본 시스템 프롬프트
SOCRATES_BASE_PROMPT = """You are Socrates, the intellectual companion for the user.
Your goal is NOT just to answer questions, but to help the user building their own "Knowledge Ontology".

**Core Rules:**
1. **Context-Aware**: Always consider the retrieved memories (provided in context) before answering.
2. **Socratic Method**: If the user asks a vague question, ask back to clarify their intent.
3. **Bridge Builder**: When you see a connection between the user's current thought and a past memory, EXPLICITLY mention it. (e.g., "This reminds me of what you noted about [Project X] last week...")
4. **Tone**: Intellectual, Supportive, Concise. Respond in the same language the user uses.

**Response Guidelines:**
- Be concise but insightful
- Draw connections between ideas
- Ask follow-up questions to deepen understanding
- Speak in Korean if the user speaks Korean"""

# 모드별 추가 프롬프트
INSIGHT_PROMPT = """
**[Insight Mode Active]**
Your goal is to help the user think more deeply about the topic.
- Ask probing questions: "What is the core assumption behind this idea?"
- Challenge surface-level thoughts: "What evidence supports this?"
- Connect to broader themes: "How does this relate to your previous thoughts on [X]?"
- Encourage reflection: "What would change if this assumption were false?"
"""

COUNTER_ARGUMENT_PROMPT = """
**[Counter-Argument Mode Active]**
Your goal is to present the opposing viewpoint to strengthen the user's thinking.
- Present the strongest counter-argument: "One could argue that..."
- Reference contradictory memories if found: "In [your note from X], you mentioned..."
- Steelman the opposition: "The strongest case against this would be..."
- End with a question: "How would you respond to this critique?"
"""

SUMMARY_PROMPT = """
**[Interactive Summary Mode Active]**
Your goal is to collaboratively create a summary of the topic.
- Start by identifying key points: "Let me summarize what I understand so far..."
- Ask for corrections: "Did I capture the essence correctly?"
- Build on user input: "So the key insight seems to be..."
- Offer structured output: "Would you like me to organize this as bullet points or paragraphs?"
"""

EVENING_RITUAL_PROMPT = """
**[Evening Ritual Mode Active]**
You are helping the user reflect on their day and consolidate learning.
- Gently prompt review: "What stood out to you today?"
- Surface recent memories: "You saved some interesting things today. Want to discuss [X]?"
- Ask synthesis questions: "What patterns do you notice in what you've been thinking about?"
- Close with intentionality: "What do you want to explore further tomorrow?"
"""


def get_mode_prompt(mode: str | None) -> str:
    """대화 모드에 따른 추가 프롬프트 반환."""
    mode_prompts = {
        "insight": INSIGHT_PROMPT,
        "counter": COUNTER_ARGUMENT_PROMPT,
        "summary": SUMMARY_PROMPT,
        "evening": EVENING_RITUAL_PROMPT,
    }
    return mode_prompts.get(mode, "")


async def find_contradicting_memories(query: str, current_memories: list) -> list:
    """현재 주제와 반대되는 메모리를 벡터 검색으로 탐색."""
    from app.config.database import get_supabase_client
    from app.repositories.vector_repository import VectorRepository

    vector_repo = VectorRepository(get_supabase_client())

    contradiction_queries = [
        f"disadvantages of {query}",
        f"problems with {query}",
        f"criticism of {query}",
        f"opposite of {query}",
    ]

    contradicting = []
    for cq in contradiction_queries[:2]:  # 쿼리 수 제한
        try:
            results = await vector_repo.similarity_search(cq, limit=2, threshold=0.4)
            for r in results:
                if r.get("id") not in [m.get("id") for m in current_memories]:
                    contradicting.append(r)
        except Exception:
            pass

    return contradicting[:3]


async def _search_vector_memories(query: str, vector_repo, limit: int = 3) -> tuple[str, list]:
    """벡터 스토어에서 관련 메모리 검색. (포맷된 텍스트, 원본 결과) 반환."""
    try:
        results = await vector_repo.similarity_search(query, limit=limit, threshold=0.5)
        if results:
            formatted = "\n".join(
                [
                    f"- [{memory.get('created_at', '')[:10]}] {memory.get('title', 'Untitled')}: {memory.get('summary') or memory.get('content', '')[:100]}..."
                    for memory in results
                ]
            )
            return formatted, results
    except Exception:
        logger.exception("Vector search failed")
    return "", []


async def _fetch_graph_context(query: str, limit: int = 8) -> str:
    """지식 그래프에서 관련 엔티티 조회. 포맷된 텍스트 반환."""
    try:
        from app.config.dependencies import get_graph_repository  # noqa: F811

        graph_repo = get_graph_repository()

        keywords = [word for word in query.split() if len(word) > 2][:3]
        graph_results = []
        for keyword in keywords:
            related = await graph_repo.get_related_context(keyword, depth=2)
            graph_results.extend(related)

        if not graph_results:
            return ""

        # 이름 기준 중복 제거
        seen = set()
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
            graph_lines.append(f"- {name} ({label}) — {rel} (depth: {dist})")
        return "\n".join(graph_lines)
    except Exception:
        logger.exception("Graph context fetch failed")
        return ""


async def _fetch_journal_context(user_id, journal_repo, limit: int = 3) -> str:
    """최근 저널 항목 조회. 포맷된 텍스트 반환."""
    try:
        recent_journals = await journal_repo.get_journals(user_id, limit=limit)
        if recent_journals:
            return "\n".join(
                [
                    f"- [Journal {journal.get('created_at', '')[:10]}] Mood: {journal.get('mood', 'N/A')} - {journal.get('content', '')[:80]}..."
                    for journal in recent_journals
                ]
            )
    except Exception:
        logger.exception("Journal context fetch failed")
    return ""


async def prepare_socrates_context(
    messages: list,
    mode: str | None = None,
    user_id: str | None = None,
) -> list:
    """Socrates용 RAG 컨텍스트가 포함된 LangChain 메시지 리스트 준비.

    벡터 검색, 저널 조회, 모드별 프롬프트를 결합하여
    LLM 호출에 바로 사용할 수 있는 메시지 리스트를 반환한다.
    """
    context_memories = ""
    contradicting_memories = ""
    graph_context = ""
    journal_context = ""
    current_memories: list = []

    last_message = messages[-1] if messages else None
    if isinstance(last_message, HumanMessage):
        query = last_message.content

        from app.config.database import get_supabase_client
        from app.repositories.vector_repository import VectorRepository

        vector_repo = VectorRepository(get_supabase_client())

        context_memories, current_memories = await _search_vector_memories(query, vector_repo)

        graph_context = await _fetch_graph_context(query)

        if user_id:
            from app.repositories.journal_repository import JournalRepository

            journal_repo = JournalRepository(get_supabase_client())
            journal_context = await _fetch_journal_context(user_id, journal_repo)

        if mode == "counter" and current_memories:
            try:
                contradicting = await find_contradicting_memories(query, current_memories)
                if contradicting:
                    contradicting_memories = "\n".join(
                        [
                            f"- [{memory.get('created_at', '')[:10]}] {memory.get('title', 'Untitled')}: {memory.get('summary') or memory.get('content', '')[:100]}..."
                            for memory in contradicting
                        ]
                    )
            except Exception:
                logger.exception("Contradiction search failed")

    system_content = SOCRATES_BASE_PROMPT
    system_content += get_mode_prompt(mode)

    if context_memories:
        system_content += f"\n\n**Retrieved Memories:**\n{context_memories}"
    if graph_context:
        system_content += f"\n\n**Knowledge Graph Context:**\n{graph_context}"
    if contradicting_memories:
        system_content += f"\n\n**Potentially Contradicting Memories:**\n{contradicting_memories}"
    if journal_context:
        system_content += f"\n\n**Recent Journal Entries:**\n{journal_context}"

    lc_messages = [SystemMessage(content=system_content)]
    for msg in messages:
        lc_messages.append(msg)

    return lc_messages


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

    lc_messages = await prepare_socrates_context(messages, mode)
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
