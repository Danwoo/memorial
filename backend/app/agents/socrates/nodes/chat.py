"""
Socrates Agent - Enhanced Conversational Interface
Phase 7: Advanced Socratic Dialogue

Features:
1. Insight Prompting - Ask probing questions
2. Counter-Argument - Present opposing viewpoints
3. Interactive Summary - Collaborative summarization
4. Evening Ritual Mode - Daily reflection session
"""
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.state import AgentState
from app.config.llm import get_streaming_llm
from app.config.settings import DEFAULT_USER_ID

logger = logging.getLogger(__name__)

# Base system prompt
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

# Mode-specific prompts
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
    """Get additional prompt based on conversation mode."""
    mode_prompts = {
        "insight": INSIGHT_PROMPT,
        "counter": COUNTER_ARGUMENT_PROMPT,
        "summary": SUMMARY_PROMPT,
        "evening": EVENING_RITUAL_PROMPT
    }
    return mode_prompts.get(mode, "")


async def find_contradicting_memories(query: str, current_memories: list) -> list:
    """Find memories that might contradict the current topic."""
    from app.config.database import get_supabase_client
    from app.repositories.vector_repository import VectorRepository

    vector_repo = VectorRepository(get_supabase_client())

    # Search for potentially contradicting content
    contradiction_queries = [
        f"disadvantages of {query}",
        f"problems with {query}",
        f"criticism of {query}",
        f"opposite of {query}"
    ]

    contradicting = []
    for cq in contradiction_queries[:2]:  # Limit queries
        try:
            results = await vector_repo.similarity_search(cq, limit=2, threshold=0.4)
            for r in results:
                if r.get("id") not in [m.get("id") for m in current_memories]:
                    contradicting.append(r)
        except Exception:
            pass

    return contradicting[:3]  # Return top 3


async def prepare_socrates_context(
    messages: list,
    mode: str | None = None,
) -> list:
    """
    Prepare LangChain message list with RAG context for Socrates.

    Performs vector search, journal retrieval, and mode-specific prompt
    building. Returns a list of LangChain messages ready for LLM invocation.
    """
    context_memories = ""
    contradicting_memories = ""
    graph_context = ""
    current_memories: list = []

    last_message = messages[-1] if messages else None
    if isinstance(last_message, HumanMessage):
        query = last_message.content

        from app.config.database import get_supabase_client
        from app.repositories.vector_repository import VectorRepository

        vector_repo = VectorRepository(get_supabase_client())

        try:
            results = await vector_repo.similarity_search(query, limit=3, threshold=0.5)
            if results:
                current_memories = results
                context_memories = "\n".join([
                    f"- [{m.get('created_at', '')[:10]}] {m.get('title', 'Untitled')}: {m.get('summary') or m.get('content', '')[:100]}..."
                    for m in results
                ])
        except Exception:
            logger.exception("Vector search failed")

        # Graph traversal: find related entities from knowledge graph
        try:
            from app.config.dependencies import get_graph_repository
            graph_repo = get_graph_repository()
            # Extract key terms from query for graph lookup
            keywords = [w for w in query.split() if len(w) > 2][:3]
            graph_results = []
            for kw in keywords:
                related = await graph_repo.get_related_context(kw, depth=2)
                graph_results.extend(related)

            if graph_results:
                # Deduplicate by name
                seen = set()
                unique_results = []
                for r in graph_results:
                    name = r.get("name", "")
                    if name and name not in seen:
                        seen.add(name)
                        unique_results.append(r)

                graph_lines = []
                for r in unique_results[:8]:
                    name = r.get("name", "")
                    label = r.get("label", "")
                    rel = r.get("rel_type", "RELATED_TO")
                    dist = r.get("distance", 1)
                    graph_lines.append(f"- {name} ({label}) — {rel} (depth: {dist})")
                graph_context = "\n".join(graph_lines)
        except Exception:
            logger.exception("Graph context fetch failed")

        journal_context = ""
        try:
            from app.config.database import get_supabase_client as _get_db
            from app.repositories.journal_repository import JournalRepository
            journal_repo = JournalRepository(_get_db())
            recent_journals = await journal_repo.get_journals(DEFAULT_USER_ID, limit=3)
            if recent_journals:
                journal_context = "\n".join([
                    f"- [Journal {j.get('created_at', '')[:10]}] Mood: {j.get('mood', 'N/A')} - {j.get('content', '')[:80]}..."
                    for j in recent_journals
                ])
        except Exception:
            logger.exception("Journal context fetch failed")

        if mode == "counter" and current_memories:
            try:
                contradicting = await find_contradicting_memories(query, current_memories)
                if contradicting:
                    contradicting_memories = "\n".join([
                        f"- [{m.get('created_at', '')[:10]}] {m.get('title', 'Untitled')}: {m.get('summary') or m.get('content', '')[:100]}..."
                        for m in contradicting
                    ])
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
    """
    Enhanced Socrates Node with multiple dialogue modes.

    Input:
        state.messages (conversation history)
        state.context.mode (optional: insight, counter, summary, evening)
    Output: Updated messages with AI response
    """
    messages = state.get("messages", [])
    context = state.get("context", {})
    mode = context.get("mode") if isinstance(context, dict) else None

    if not messages:
        greeting = "안녕하세요! 무엇을 도와드릴까요?"
        if mode == "evening":
            greeting = "🌙 오늘 하루 어떠셨나요? 오늘 저장한 내용들을 함께 돌아볼까요?"
        return {
            "messages": [AIMessage(content=greeting)],
            "next_step": "end"
        }

    lc_messages = await prepare_socrates_context(messages, mode)
    llm = get_streaming_llm()

    try:
        response = await llm.ainvoke(lc_messages)
        return {
            "messages": [response],
            "next_step": "end"
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"죄송합니다, 오류가 발생했습니다: {str(e)}")],
            "next_step": "end",
            "error": str(e)
        }
