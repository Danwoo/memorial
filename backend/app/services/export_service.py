import asyncio
import io
import json
import logging
import zipfile
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.repositories.chat_repository import ChatRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.protocols.scrap_repository_protocol import ScrapRepositoryProtocol

logger = logging.getLogger(__name__)

MAX_EXPORT_LIMIT = 10000


class ExportService:
    """사용자 데이터 내보내기 비즈니스 로직."""

    def __init__(
        self,
        scrap_repo: ScrapRepositoryProtocol,
        diary_repo: DiaryRepository,
        chat_repo: ChatRepository,
    ):
        self.scrap_repo = scrap_repo
        self.diary_repo = diary_repo
        self.chat_repo = chat_repo

    async def export_scraps(self, user_id: UUID) -> list[dict[str, Any]]:
        """사용자의 전체 스크랩을 JSON 직렬화 가능한 리스트로 반환."""
        return await self.scrap_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT)

    async def export_diaries_zip(self, user_id: UUID) -> bytes:
        """사용자의 전체 다이어리를 Markdown ZIP으로 반환."""
        diaries = await self.diary_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in diaries:
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
        """전체 데이터 통합 내보내기 (scraps + diaries + chat sessions)."""
        scraps, diaries, sessions = await asyncio.gather(
            self.scrap_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
            self.diary_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
            self.chat_repo.get_sessions_for_export(user_id, MAX_EXPORT_LIMIT),
        )

        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "scraps": scraps,
            "diaries": diaries,
            "chat_sessions": [s.model_dump(mode="json") for s in sessions],
        }

    async def get_export_counts(self, user_id: UUID) -> dict[str, int]:
        """내보내기 미리보기용 데이터 건수 조회."""
        scraps, diaries = await asyncio.gather(
            self.scrap_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
            self.diary_repo.get_all_for_export(user_id, MAX_EXPORT_LIMIT),
        )

        return {
            "scraps": len(scraps),
            "diaries": len(diaries),
        }
