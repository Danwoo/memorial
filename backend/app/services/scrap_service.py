import contextlib
import logging
from uuid import UUID

from app.repositories.protocols.mindmap_repository_protocol import MindmapRepositoryProtocol
from app.repositories.protocols.scrap_repository_protocol import ScrapRepositoryProtocol
from app.repositories.protocols.vector_repository_protocol import VectorRepositoryProtocol
from app.schemas.scrap_schema import ScrapInDB, SourceType
from app.services.korean_tokenizer import tokenize, tokens_to_tsvector_input
from app.utils.cache import stats_cache, tags_cache

logger = logging.getLogger(__name__)


class ScrapService:
    """Scrap CRUD 및 임베딩/마인드맵 연동 비즈니스 로직."""

    def __init__(
        self, scrap_repo: ScrapRepositoryProtocol, vector_repo: VectorRepositoryProtocol, mindmap_repo: MindmapRepositoryProtocol | None = None
    ):
        self.scrap_repo = scrap_repo
        self.vector_repo = vector_repo
        self.mindmap_repo = mindmap_repo

    async def create_scrap(
        self,
        user_id: UUID,
        title: str,
        content: str,
        source_type: SourceType,
        source_url: str | None = None,
        summary: str | None = None,
    ) -> ScrapInDB:
        """새 Scrap 생성 후 임베딩 자동 생성."""
        scrap = await self.scrap_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            source_type=source_type,
            source_url=source_url,
            summary=summary,
        )

        embed_text = f"{scrap.title}\n\n{scrap.content}"
        await self.vector_repo.save_embedding(scrap_id=str(scrap.id), content=embed_text)

        # 검색용 토큰 저장 (sparse search)
        await self._save_search_tokens(str(scrap.id), embed_text)

        # 통계/태그 캐시 무효화
        stats_cache.invalidate_prefix(f"user:{user_id}")
        tags_cache.invalidate(f"user:{user_id}:tags")

        return scrap

    async def get_scrap(self, scrap_id: UUID, user_id: UUID) -> ScrapInDB | None:
        """ID로 Scrap 조회."""
        return await self.scrap_repo.get_by_id(scrap_id, user_id)

    async def list_scraps(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        search: str | None = None,
        tags: list[str] | None = None,
        source_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ScrapInDB], int]:
        """페이지네이션 Scrap 목록 조회."""
        return await self.scrap_repo.get_by_user(
            user_id=user_id,
            page=page,
            limit=limit,
            search=search,
            tags=tags,
            source_type=source_type,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def update_scrap_after_processing(
        self,
        scrap_id: UUID,
        summary: str,
        tags: list[str],
        entities: list[dict] | None = None,
        relations: list[dict] | None = None,
        source_type: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Librarian 처리 후 Scrap 업데이트. summary, tags, 마인드맵 데이터 저장."""
        success = await self.scrap_repo.update_status(
            memory_id=scrap_id,
            status="completed",
            summary=summary,
            tags=tags,
            source_type=source_type,
            extracted_entities=entities or [],
            extracted_relations=relations or [],
            user_id=UUID(user_id) if user_id else None,
        )

        if self.mindmap_repo and entities:
            await self.mindmap_repo.save_entities(entities, str(scrap_id), user_id)

        if self.mindmap_repo and relations:
            await self.mindmap_repo.save_relations(relations)

        # Librarian 처리 후 요약+태그+원본 title 포함하여 토큰 갱신 (원본 키워드 보존)
        if success and summary:
            tags_text = " ".join(tags) if tags else ""
            entity_names = " ".join(e.get("name", "") for e in (entities or []))
            title_text = ""
            if user_id:
                try:
                    scrap_obj = await self.scrap_repo.get_by_id(scrap_id, UUID(user_id))
                    if scrap_obj:
                        title_text = scrap_obj.title or ""
                except Exception:
                    pass
            token_source = f"{title_text} {summary} {tags_text} {entity_names}".strip()
            await self._save_search_tokens(str(scrap_id), token_source)

        return success

    async def update_scrap(
        self,
        scrap_id: UUID,
        user_id: UUID,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> ScrapInDB | None:
        """사용자가 직접 스크랩 필드를 수정."""
        fields: dict = {}
        if title is not None:
            fields["title"] = title
        if summary is not None:
            fields["summary"] = summary
        if tags is not None:
            fields["tags"] = tags

        if not fields:
            return await self.scrap_repo.get_by_id(scrap_id, user_id)

        updated = await self.scrap_repo.update_fields(scrap_id, user_id, **fields)

        if updated and self.mindmap_repo and tags is not None:
            with contextlib.suppress(Exception):
                await self.mindmap_repo.delete_memory_node(str(scrap_id))

        return updated

    async def get_user_tags(self, user_id: UUID, prefix: str = "") -> list[str]:
        """사용자의 기존 태그 목록 조회 (자동완성용)."""
        return await self.scrap_repo.get_distinct_tags(user_id, prefix)

    async def bulk_action(
        self,
        action: str,
        scrap_ids: list[UUID],
        user_id: UUID,
        tags: list[str] | None = None,
    ) -> int:
        """스크랩 일괄 작업 수행 (삭제, 태그 추가, 태그 제거)."""
        if action == "delete":
            count = await self.scrap_repo.delete_bulk(scrap_ids, user_id)
            if self.mindmap_repo:
                for mid in scrap_ids:
                    with contextlib.suppress(Exception):
                        await self.mindmap_repo.delete_memory_node(str(mid))
            return count
        if action == "add_tags" and tags:
            return await self.scrap_repo.add_tags_bulk(scrap_ids, user_id, tags)
        if action == "remove_tags" and tags:
            return await self.scrap_repo.remove_tags_bulk(scrap_ids, user_id, tags)
        return 0

    async def _save_search_tokens(self, scrap_id: str, text: str) -> None:
        """텍스트를 형태소 분석하여 search_tokens tsvector에 저장."""
        try:
            tokens = tokenize(text)
            token_string = tokens_to_tsvector_input(tokens)
            if token_string:
                await self.scrap_repo.update_search_tokens(scrap_id, token_string)
        except Exception:
            logger.warning("search_tokens 저장 실패: scrap_id=%s", scrap_id, exc_info=True)

    async def delete_scrap(self, scrap_id: UUID, user_id: UUID) -> bool:
        """Scrap 및 연관 마인드맵 데이터 삭제."""
        deleted = await self.scrap_repo.delete(scrap_id, user_id)
        if deleted:
            if self.mindmap_repo:
                await self.mindmap_repo.delete_memory_node(str(scrap_id))
            # 통계/태그 캐시 무효화
            stats_cache.invalidate_prefix(f"user:{user_id}")
            tags_cache.invalidate(f"user:{user_id}:tags")
        return deleted
