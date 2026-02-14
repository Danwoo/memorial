import asyncio
import io
import json
import logging
import zipfile
from typing import Any
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)

MAX_EXPORT_LIMIT = 10000


class ExportService:
    """사용자 데이터 내보내기 비즈니스 로직."""

    def __init__(self, db: Client):
        self.db = db

    async def export_memories(self, user_id: UUID) -> list[dict[str, Any]]:
        """사용자의 전체 메모리를 JSON 직렬화 가능한 리스트로 반환."""
        response = await asyncio.to_thread(
            lambda: self.db.table("memories")
            .select("id, title, summary, content, tags, source_url, source_type, created_at, updated_at")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(MAX_EXPORT_LIMIT)
            .execute()
        )
        return response.data

    async def export_journals_zip(self, user_id: UUID) -> bytes:
        """사용자의 전체 저널을 Markdown ZIP으로 반환."""
        response = await asyncio.to_thread(
            lambda: self.db.table("journals")
            .select("id, content, mood, tags, created_at, updated_at")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(MAX_EXPORT_LIMIT)
            .execute()
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in response.data:
                date_str = (entry.get("created_at") or "unknown")[:10]
                entry_id = (entry.get("id") or "unknown")[:8]
                filename = f"{date_str}_{entry_id}.md"

                # YAML frontmatter
                frontmatter_lines = ["---"]
                if entry.get("mood"):
                    frontmatter_lines.append(f"mood: {entry['mood']}")
                if entry.get("tags"):
                    frontmatter_lines.append(f"tags: {json.dumps(entry['tags'], ensure_ascii=False)}")
                frontmatter_lines.append(f"created_at: {entry.get('created_at', '')}")
                frontmatter_lines.append("---\n")

                content = "\n".join(frontmatter_lines) + (entry.get("content") or "")
                zf.writestr(filename, content)

        return buf.getvalue()

    async def export_all(self, user_id: UUID) -> dict[str, Any]:
        """전체 데이터 통합 내보내기 (memories + journals + chat_sessions)."""
        uid = str(user_id)

        memories_task = asyncio.to_thread(
            lambda: self.db.table("memories")
            .select("id, title, summary, content, tags, source_url, source_type, created_at, updated_at")
            .eq("user_id", uid)
            .order("created_at", desc=True)
            .limit(MAX_EXPORT_LIMIT)
            .execute()
        )

        journals_task = asyncio.to_thread(
            lambda: self.db.table("journals")
            .select("id, content, mood, tags, created_at, updated_at")
            .eq("user_id", uid)
            .order("created_at", desc=True)
            .limit(MAX_EXPORT_LIMIT)
            .execute()
        )

        sessions_task = asyncio.to_thread(
            lambda: self.db.table("chat_sessions")
            .select("id, title, created_at")
            .eq("user_id", uid)
            .order("created_at", desc=True)
            .limit(MAX_EXPORT_LIMIT)
            .execute()
        )

        memories_resp, journals_resp, sessions_resp = await asyncio.gather(
            memories_task,
            journals_task,
            sessions_task,
        )

        return {
            "exported_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "memories": memories_resp.data,
            "journals": journals_resp.data,
            "chat_sessions": sessions_resp.data,
        }

    async def get_export_counts(self, user_id: UUID) -> dict[str, int]:
        """내보내기 미리보기용 데이터 건수 조회."""
        uid = str(user_id)

        memories_task = asyncio.to_thread(
            lambda: self.db.table("memories").select("id", count="exact").eq("user_id", uid).execute()
        )

        journals_task = asyncio.to_thread(
            lambda: self.db.table("journals").select("id", count="exact").eq("user_id", uid).execute()
        )

        memories_resp, journals_resp = await asyncio.gather(memories_task, journals_task)

        return {
            "memories": memories_resp.count or 0,
            "journals": journals_resp.count or 0,
        }
