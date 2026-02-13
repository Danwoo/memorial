import contextlib
from uuid import UUID

from app.repositories.graph_repository import GraphRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.memory_schema import MemoryInDB, SourceType


class MemoryService:
    """Memory CRUD 및 임베딩/그래프 연동 비즈니스 로직."""

    def __init__(
        self, memory_repo: MemoryRepository, vector_repo: VectorRepository, graph_repo: GraphRepository | None = None
    ):
        self.memory_repo = memory_repo
        self.vector_repo = vector_repo
        self.graph_repo = graph_repo

    async def create_memory(
        self,
        user_id: UUID,
        title: str,
        content: str,
        source_type: SourceType,
        source_url: str | None = None,
        summary: str | None = None,
    ) -> MemoryInDB:
        """새 Memory 생성 후 임베딩 자동 생성."""
        memory = await self.memory_repo.create(
            user_id=user_id,
            title=title,
            content=content,
            source_type=source_type,
            source_url=source_url,
            summary=summary,
        )

        await self.vector_repo.save_embedding(memory_id=str(memory.id), content=f"{memory.title}\n\n{memory.content}")

        return memory

    async def get_memory(self, memory_id: UUID, user_id: UUID) -> MemoryInDB | None:
        """ID로 Memory 조회."""
        return await self.memory_repo.get_by_id(memory_id, user_id)

    async def list_memories(
        self, user_id: UUID, page: int = 1, limit: int = 20, search: str | None = None
    ) -> tuple[list[MemoryInDB], int]:
        """페이지네이션 Memory 목록 조회."""
        return await self.memory_repo.get_by_user(user_id=user_id, page=page, limit=limit, search=search)

    async def update_memory_after_processing(
        self,
        memory_id: UUID,
        summary: str,
        tags: list[str],
        entities: list[dict] | None = None,
        relations: list[dict] | None = None,
        source_url: str | None = None,
        source_type: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Librarian 처리 후 Memory 업데이트. summary, tags, 그래프 데이터 저장."""
        success = await self.memory_repo.update_status(
            memory_id=memory_id,
            status="completed",
            summary=summary,
            tags=tags,
            source_url=source_url,
            source_type=source_type,
        )

        if self.graph_repo and entities:
            await self.graph_repo.save_entities(entities, str(memory_id), user_id)

        if self.graph_repo and relations:
            await self.graph_repo.save_relations(relations)

        return success

    async def update_memory(
        self,
        memory_id: UUID,
        user_id: UUID,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryInDB | None:
        """사용자가 직접 메모리 필드를 수정."""
        fields: dict = {}
        if title is not None:
            fields["title"] = title
        if summary is not None:
            fields["summary"] = summary
        if tags is not None:
            fields["tags"] = tags

        if not fields:
            return await self.memory_repo.get_by_id(memory_id, user_id)

        updated = await self.memory_repo.update_fields(memory_id, user_id, **fields)

        if updated and self.graph_repo and tags is not None:
            with contextlib.suppress(Exception):
                await self.graph_repo.delete_memory_node(str(memory_id))

        return updated

    async def get_user_tags(self, user_id: UUID, prefix: str = "") -> list[str]:
        """사용자의 기존 태그 목록 조회 (자동완성용)."""
        return await self.memory_repo.get_distinct_tags(user_id, prefix)

    async def bulk_action(
        self,
        action: str,
        memory_ids: list[UUID],
        user_id: UUID,
        tags: list[str] | None = None,
    ) -> int:
        """메모리 일괄 작업 수행 (삭제, 태그 추가, 태그 제거)."""
        if action == "delete":
            count = await self.memory_repo.delete_bulk(memory_ids, user_id)
            if self.graph_repo:
                for mid in memory_ids:
                    with contextlib.suppress(Exception):
                        await self.graph_repo.delete_memory_node(str(mid))
            return count
        elif action == "add_tags" and tags:
            return await self.memory_repo.add_tags_bulk(memory_ids, user_id, tags)
        elif action == "remove_tags" and tags:
            return await self.memory_repo.remove_tags_bulk(memory_ids, user_id, tags)
        return 0

    async def delete_memory(self, memory_id: UUID, user_id: UUID) -> bool:
        """Memory 및 연관 그래프 데이터 삭제."""
        deleted = await self.memory_repo.delete(memory_id, user_id)
        if deleted and self.graph_repo:
            await self.graph_repo.delete_memory_node(str(memory_id))
        return deleted
