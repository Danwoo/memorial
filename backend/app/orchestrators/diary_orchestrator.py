"""다이어리 도메인의 cross-domain 흐름 조율.

다이어리 작성은 다음과 같이 여러 도메인을 거친다:
- diary (생성/저장)
- scrap (생성: 다이어리를 KB의 일부로 적재)
- librarian agent (엔티티/관계 추출 후 그래프 적재)

이런 다중 도메인 협업을 다이어리 router나 service가 직접 호출하면 prefix 의존성이 깨진다.
Orchestrator는 명시적 cross-domain 경계로서, 이런 흐름의 위치를 한곳에 모은다.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.agents.librarian.graph import librarian_graph
from app.agents.state import build_librarian_initial_state
from app.services.scrap_service import ScrapService

logger = logging.getLogger(__name__)

# 처리 임계값 (너무 짧으면 엔티티 추출 가치 없음, 너무 길면 토큰 비용)
MIN_DIARY_LENGTH_FOR_EXTRACTION = 50
DIARY_TEXT_TRUNCATE_CHARS = 6000


class DiaryOrchestrator:
    """다이어리 cross-domain 흐름 조율."""

    def __init__(self, scrap_service: ScrapService):
        self.scrap_service = scrap_service

    async def process_diary_with_librarian(
        self,
        diary_id: str,
        content: str,
        user_id: str,
    ) -> None:
        """다이어리 내용을 스크랩으로 저장 후 Librarian 엔티티 추출.

        백그라운드 task로 호출되며, 실패해도 다이어리 자체는 이미 저장됐으므로
        graceful degradation (warning 로깅 + 종료).
        """
        try:
            scrap = await self.scrap_service.create_scrap(
                user_id=UUID(user_id),
                title=f"다이어리 {diary_id[:8]}",
                content=content[:DIARY_TEXT_TRUNCATE_CHARS],
                source_type="DIARY",
            )
            if not scrap:
                logger.warning("Failed to create scrap for diary %s", diary_id)
                return

            scrap_id = str(scrap.id)

            initial_state = build_librarian_initial_state(
                scrap_id, content[:DIARY_TEXT_TRUNCATE_CHARS], user_id
            )
            result = await librarian_graph.ainvoke(initial_state)
            logger.info(
                "Librarian processed diary %s: classification=%s",
                diary_id,
                result.get("classification"),
            )
        except Exception:
            # 백그라운드 task — 실패해도 다이어리 자체는 저장됐으므로 로깅만
            logger.exception("Librarian processing failed for diary %s", diary_id)
