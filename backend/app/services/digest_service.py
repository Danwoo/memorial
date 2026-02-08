"""
Digest Service
Business logic for daily digest - aggregates today's memories, chats, and journals
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config.settings import get_settings, DEFAULT_USER_ID

logger = logging.getLogger(__name__)


DIGEST_QUESTION_PROMPT = """Based on the user's collected memories from today, generate 1-2 thoughtful questions 
to help them reflect on their day. Focus on:
1. Connections between different pieces of content
2. Potential insights or learnings
3. How this relates to their ongoing projects or interests

Respond in Korean. Return only the questions, one per line."""


class DigestService:
    """Service for daily digest aggregation and AI-powered insights."""
    
    def __init__(self, memory_repo, journal_repo, chat_repo=None):
        self.memory_repo = memory_repo
        self.journal_repo = journal_repo
        self.chat_repo = chat_repo
        self.settings = get_settings()
    
    async def get_today_digest(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get comprehensive digest of today's activities.
        
        Returns:
            - memories: Today's saved memories/resources
            - journals: Today's journal entries
            - chats: Today's chat sessions (if available)
            - insights: AI-generated questions and topics
        """
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # 1. Get today's memories
        memories = await self._get_today_memories(today_start, today_end)
        
        # 2. Get today's journals
        journals = self._get_today_journals(user_id, today)
        
        # 3. Get today's chats (placeholder - requires chat history implementation)
        chats = []  # TODO: Implement when chat history is available
        
        # 4. Extract main topics
        main_topics = self._extract_topics(memories)
        
        # 5. Generate AI questions
        suggested_questions = await self._generate_questions(memories, journals)
        
        return {
            "date": today.isoformat(),
            "summary": {
                "memory_count": len(memories),
                "journal_count": len(journals),
                "chat_count": len(chats)
            },
            "memories": [
                {
                    "id": str(m.get("id", "")),
                    "title": m.get("title", "Untitled"),
                    "type": m.get("source_type", "UNKNOWN"),
                    "summary": m.get("summary") or m.get("content", "")[:150],
                    "tags": m.get("tags", []),
                    "created_at": m.get("created_at", "")
                }
                for m in memories[:10]  # Limit to 10
            ],
            "journals": [
                {
                    "id": str(j.get("id", "")),
                    "mood": j.get("mood", "NEUTRAL"),
                    "preview": j.get("content", "")[:100],
                    "created_at": j.get("created_at", "")
                }
                for j in journals[:5]  # Limit to 5
            ],
            "chats": chats,
            "insights": {
                "main_topics": main_topics[:5],
                "suggested_questions": suggested_questions
            }
        }
    
    async def _get_today_memories(self, start: datetime, end: datetime) -> List[Dict]:
        """Get memories created today."""
        try:
            # Using the memory repository to get memories
            all_memories = await self.memory_repo.get_all()
            
            today_memories = []
            for m in all_memories:
                created_at_str = m.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                        if start <= created_at <= end:
                            today_memories.append(m)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping memory with unparseable date: %s", e)

            return today_memories
        except Exception as e:
            logger.exception("Error fetching today's memories")
            return []
    
    def _get_today_journals(self, user_id: Optional[UUID], today: datetime) -> List[Dict]:
        """Get journals created today."""
        try:
            # Get recent journals and filter by today
            journals = self.journal_repo.get_journals(
                user_id or DEFAULT_USER_ID,
                limit=20
            )
            
            today_journals = []
            for j in journals:
                created_at_str = j.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                        if created_at.date() == today:
                            today_journals.append(j)
                    except (ValueError, TypeError) as e:
                        logger.debug("Skipping journal with unparseable date: %s", e)

            return today_journals
        except Exception as e:
            logger.exception("Error fetching today's journals")
            return []
    
    def _extract_topics(self, memories: List[Dict]) -> List[str]:
        """Extract main topics from memories based on tags."""
        tag_counts = {}
        for m in memories:
            for tag in m.get("tags", []) or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count and return top tags
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags]
    
    async def _generate_questions(
        self, 
        memories: List[Dict], 
        journals: List[Dict]
    ) -> List[str]:
        """Generate AI-powered reflection questions based on today's content."""
        if not memories and not journals:
            return ["오늘 하루는 어떠셨나요?"]
        
        # Build context from memories and journals
        context_parts = []
        
        for m in memories[:5]:
            title = m.get("title", "Untitled")
            summary = m.get("summary") or m.get("content", "")[:100]
            context_parts.append(f"- {title}: {summary}")
        
        for j in journals[:2]:
            mood = j.get("mood", "NEUTRAL")
            preview = j.get("content", "")[:100]
            context_parts.append(f"- [Journal, Mood: {mood}] {preview}")
        
        if not context_parts:
            return ["오늘 저장한 내용들을 돌아보면서 어떤 생각이 드시나요?"]
        
        try:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=self.settings.OPENAI_API_KEY
            )
            
            messages = [
                SystemMessage(content=DIGEST_QUESTION_PROMPT),
                HumanMessage(content=f"Today's content:\n" + "\n".join(context_parts))
            ]
            
            response = llm.invoke(messages)
            questions = [q.strip() for q in response.content.split('\n') if q.strip()]
            return questions[:2]
            
        except Exception as e:
            logger.exception("Error generating questions")
            return ["오늘 저장한 내용들에서 어떤 인사이트를 얻으셨나요?"]
