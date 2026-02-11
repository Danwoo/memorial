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

    async def delete_memory(self, memory_id: UUID, user_id: UUID) -> bool:
        """Memory 및 연관 그래프 데이터 삭제."""
        deleted = await self.memory_repo.delete(memory_id, user_id)
        if deleted and self.graph_repo:
            await self.graph_repo.delete_memory_node(str(memory_id))
        return deleted
