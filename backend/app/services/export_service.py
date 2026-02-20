import asyncio
import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.repositories.chat_repository import ChatRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)

MAX_EXPORT_LIMIT = 10000


class ExportService:
    """사용자 데이터 내보내기 비즈니스 로직."""

    def __init__(
        self,
        memory_repo: MemoryRepository,
        journal_repo: JournalRepository,
        chat_repo: ChatRepository,
    ):
        self.memory_repo = memory_repo
        self.journal_repo = journal_repo
        self.chat_repo = chat_repo

    async def export_memories(self, user_id: UUID) -> list[dict[str, Any]]:
        """사용자의 전체 메모리를 JSON 직렬화 가능한 리스트로 반환."""
        return await self.memory_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT)

    async def export_journals_zip(self, user_id: UUID) -> bytes:
        """사용자의 전체 저널을 Markdown ZIP으로 반환."""
        journals = await self.journal_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in journals:
                date_str = (entry.get("created_at") or "unknown")[:10]
                entry_id = (entry.get("id") or "unknown")[:8]
                filename = f"{date_str}_{entry_id}.md"

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
        memories, journals, sessions = await asyncio.gather(
            self.memory_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
            self.journal_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
            self.chat_repo.get_sessions_for_export(user_id, MAX_EXPORT_LIMIT),
        )

        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "memories": memories,
            "journals": journals,
            "chat_sessions": sessions,
        }

    async def get_export_counts(self, user_id: UUID) -> dict[str, int]:
        """내보내기 미리보기용 데이터 건수 조회."""
        memories, journals = await asyncio.gather(
            self.memory_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
            self.journal_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
        )

        return {
            "memories": len(memories),
            "journals": len(journals),
        }
