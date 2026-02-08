from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from app.config.settings import get_settings
from supabase import create_client, Client

class JournalRepository:
    def __init__(self):
        settings = get_settings()
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)

    def create_journal(self, user_id: Optional[UUID] = None, content: str = "", mood: Optional[str] = None, tags: List[str] = []) -> Dict[str, Any]:
        """Create a new journal entry."""
        data = {
            "content": content,
            "mood": mood,
            "tags": tags,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Only include user_id if provided (dev mode may skip)
        if user_id:
            data["user_id"] = str(user_id)
        
        response = self.supabase.table("journals").insert(data).execute()
        return response.data[0] if response.data else None

    def get_journals(self, user_id: UUID, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of journals for a user."""
        response = self.supabase.table("journals")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        return response.data

    def update_journal(self, journal_id: UUID, content: str, mood: Optional[str] = None) -> Dict[str, Any]:
        """Update a journal entry."""
        data = {
            "content": content,
            "updated_at": datetime.now().isoformat()
        }
        if mood:
            data["mood"] = mood
            
        response = self.supabase.table("journals").update(data).eq("id", str(journal_id)).execute()
        return response.data[0] if response.data else None
