"""
Stats Repository
Data access layer for statistics queries from Supabase
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase import Client


class StatsRepository:
    """Repository for statistics data queries"""
    
    def __init__(self, db: Client):
        self.db = db
    
    async def get_all_memories(self) -> List[Dict[str, Any]]:
        """Get all memories for statistics calculation."""
        result = self.db.table("memories").select("*").execute()
        return result.data or []
    
    async def get_memories_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get memories created within a date range."""
        result = self.db.table("memories").select("*").gte(
            "created_at", start_date.isoformat()
        ).lte(
            "created_at", end_date.isoformat()
        ).execute()
        return result.data or []
    
    async def get_memories_by_date(
        self,
        page: int = 1,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get memories ordered by date for timeline."""
        offset = (page - 1) * limit
        
        result = self.db.table("memories").select(
            "id, title, summary, source_type, tags, created_at"
        ).order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        return result.data or []
    
    async def count_by_source_type(self) -> Dict[str, int]:
        """Count memories grouped by source type."""
        result = self.db.table("memories").select("source_type").execute()
        
        counts: Dict[str, int] = {}
        for row in result.data or []:
            source_type = row.get("source_type", "UNKNOWN")
            counts[source_type] = counts.get(source_type, 0) + 1
        
        return counts
    
    async def get_tag_counts(self, limit: int = 10) -> Dict[str, int]:
        """Get top tags by usage count."""
        result = self.db.table("memories").select("tags").execute()
        
        tag_counts: Dict[str, int] = {}
        for row in result.data or []:
            tags = row.get("tags") or []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort and limit
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:limit])
