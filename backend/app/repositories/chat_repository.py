"""
Chat Repository
Data access layer for chat sessions - Supabase implementation
"""
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from supabase import Client
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class ChatRepository:
    """Repository for chat session operations with Supabase persistence"""
    
    def __init__(self, db: Client):
        self.db = db
    
    async def create_session(
        self,
        user_id: UUID,
        title: Optional[str] = None
    ) -> dict:
        """Create a new chat session in Supabase."""
        title = title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        data = {
            "user_id": str(user_id),
            "title": title
        }
        
        result = self.db.table("chat_sessions").insert(data).execute()
        
        if result.data:
            session = result.data[0]
            return {
                "id": session["id"],
                "user_id": session["user_id"],
                "title": session["title"],
                "created_at": session["created_at"]
            }
        
        # Fallback - should not happen
        session_id = str(uuid4())
        return {
            "id": session_id,
            "user_id": str(user_id),
            "title": title,
            "created_at": datetime.now().isoformat()
        }
    
    async def get_session(self, session_id: UUID) -> Optional[dict]:
        """Get a session by ID from Supabase."""
        result = self.db.table("chat_sessions") \
            .select("*") \
            .eq("id", str(session_id)) \
            .execute()
        
        if result.data and len(result.data) > 0:
            session = result.data[0]
            return {
                "id": session["id"],
                "user_id": session["user_id"],
                "title": session["title"],
                "created_at": session["created_at"]
            }
        return None
    
    async def get_sessions_by_user(self, user_id: UUID) -> List[dict]:
        """Get all sessions for a user from Supabase."""
        result = self.db.table("chat_sessions") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .execute()
        
        return [
            {
                "id": s["id"],
                "user_id": s["user_id"],
                "title": s["title"],
                "created_at": s["created_at"]
            }
            for s in result.data
        ] if result.data else []
    
    async def add_message(
        self,
        session_id: UUID,
        message: BaseMessage
    ) -> bool:
        """Add a message to a session in Supabase."""
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        content = message.content if hasattr(message, 'content') else str(message)
        
        data = {
            "session_id": str(session_id),
            "role": role,
            "content": content
        }
        
        try:
            self.db.table("chat_messages").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error adding message to Supabase: {e}")
            return False
    
    async def get_messages(self, session_id: UUID) -> List[BaseMessage]:
        """Get all messages in a session from Supabase."""
        result = self.db.table("chat_messages") \
            .select("*") \
            .eq("session_id", str(session_id)) \
            .order("created_at", desc=False) \
            .execute()
        
        messages = []
        if result.data:
            for msg in result.data:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        return messages
    
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session and its messages from Supabase."""
        try:
            # Messages are deleted via CASCADE in DB
            self.db.table("chat_sessions") \
                .delete() \
                .eq("id", str(session_id)) \
                .execute()
            return True
        except Exception as e:
            print(f"Error deleting session from Supabase: {e}")
            return False
