"""
Memory Repository
Data access layer for memories table in Supabase
"""
from typing import Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime, timezone
from supabase import Client

from app.schemas.memory import MemoryInDB, SourceType


class MemoryRepository:
    """Repository for memory CRUD operations"""
    
    def __init__(self, db: Client):
        self.db = db
    
    async def create(
        self,
        user_id: UUID,
        title: str,
        content: str,
        source_type: SourceType,
        source_url: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> MemoryInDB:
        """
        Create a new memory record.
        Returns the created memory with generated ID.
        """
        memory_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()
        
        data = {
            "id": str(memory_id),
            "user_id": str(user_id),
            "title": title,
            "content": content,
            "source_type": source_type,
            "summary": summary,
            "status": "processing",
            "created_at": now,
            "updated_at": now,
        }
        
        result = self.db.table("memories").insert(data).execute()
        
        if result.data:
            return self._row_to_model(result.data[0])
        
        raise Exception("Failed to create memory")
    
    async def get_by_id(
        self,
        memory_id: UUID,
        user_id: UUID
    ) -> Optional[MemoryInDB]:
        """Get a single memory by ID (with user_id for RLS)."""
        result = self.db.table("memories").select("*").eq(
            "id", str(memory_id)
        ).eq("user_id", str(user_id)).single().execute()
        
        if result.data:
            return self._row_to_model(result.data)
        return None
    
    async def get_all(
        self,
        user_id: Optional[UUID] = None,
        limit: int = 1000
    ) -> List[dict]:
        """
        Get all memories as raw dicts for internal services (digest, graph).

        Args:
            user_id: Optional user filter. If None, returns all memories.
            limit: Maximum number of records to return.

        Returns:
            List of memory dicts from Supabase.
        """
        query = self.db.table("memories").select("*")

        if user_id:
            query = query.eq("user_id", str(user_id))

        query = query.order("created_at", desc=True).limit(limit)
        result = query.execute()

        return result.data or []

    async def get_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> Tuple[List[MemoryInDB], int]:
        """
        Get paginated list of memories for a user.
        Returns (items, total_count)
        """
        offset = (page - 1) * limit
        
        query = self.db.table("memories").select("*", count="exact").eq(
            "user_id", str(user_id)
        )
        
        if search:
            # Escape special SQL LIKE characters to prevent filter injection
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.or_(f"title.ilike.%{escaped}%,content.ilike.%{escaped}%")
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        items = [self._row_to_model(row) for row in (result.data or [])]
        total = result.count if result.count else 0
        
        return items, total
    
    async def update_status(
        self,
        memory_id: UUID,
        status: str,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> bool:
        """
        Update memory status and optionally summary/tags.
        Used after Librarian agent processes the memory.
        """
        now = datetime.now(timezone.utc).isoformat()
        
        update_data = {
            "status": status,
            "updated_at": now
        }
        
        if summary is not None:
            update_data["summary"] = summary
        
        if tags is not None:
            update_data["tags"] = tags
            
        if source_url is not None:
            update_data["source_url"] = source_url
            
        if source_type is not None:
            update_data["source_type"] = source_type
        
        result = self.db.table("memories").update(update_data).eq(
            "id", str(memory_id)
        ).execute()
        
        return len(result.data) > 0 if result.data else False
    
    async def delete(
        self,
        memory_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a memory by ID."""
        result = self.db.table("memories").delete().eq(
            "id", str(memory_id)
        ).eq("user_id", str(user_id)).execute()
        
        return len(result.data) > 0 if result.data else False
    
    def _row_to_model(self, row: dict) -> MemoryInDB:
        """Convert database row to Pydantic model."""
        return MemoryInDB(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            title=row["title"],
            content=row["content"],
            summary=row.get("summary"),
            source_url=row.get("source_url"),
            source_type=row["source_type"],
            status=row.get("status", "pending"),
            tags=row.get("tags"),
            created_at=datetime.fromisoformat(
                row["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"].replace("Z", "+00:00")
            ) if row.get("updated_at") else None
        )
