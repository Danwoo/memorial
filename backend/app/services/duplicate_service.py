import asyncio
import logging
from uuid import UUID

from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.duplicate_schema import DuplicatePair, DuplicatePairItem

logger = logging.getLogger(__name__)

VECTOR_SIMILARITY_THRESHOLD = 0.90


class DuplicateService:
    """메모리 중복 감지 및 병합 서비스."""

    def __init__(self, memory_repo: MemoryRepository, vector_repo: VectorRepository):
        self.memory_repo = memory_repo
        self.vector_repo = vector_repo

    async def find_duplicates(self, user_id: UUID) -> list[DuplicatePair]:
        """URL 정확 매칭 + 벡터 유사도 기반 중복 쌍 탐지."""
        items, _ = await self.memory_repo.get_by_user(user_id=user_id, page=1, limit=200)
        if len(items) < 2:
            return []

        pairs: list[DuplicatePair] = []
        seen: set[tuple[str, str]] = set()

        # 1. URL 정확 매칭
        url_map: dict[str, list] = {}
        for item in items:
            if item.source_url:
                url_map.setdefault(item.source_url, []).append(item)

        for _url, group in url_map.items():
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    key = (str(min(a.id, b.id)), str(max(a.id, b.id)))
                    if key in seen:
                        continue
                    seen.add(key)
                    pairs.append(
                        DuplicatePair(
                            memory_a=self._to_pair_item(a),
                            memory_b=self._to_pair_item(b),
                            similarity=1.0,
                            reason="동일 URL",
                        )
                    )

        # 2. 벡터 유사도 검색 (상위 항목만 샘플링)
        sample = items[:50]
        for item in sample:
            if not item.content:
                continue
            try:
                results = await self.vector_repo.similarity_search(
                    query=item.title + "\n" + (item.summary or ""),
                    limit=3,
                    threshold=VECTOR_SIMILARITY_THRESHOLD,
                    filters={"user_id": str(user_id)},
                )
                for r in results:
                    other_id = r.get("id", "")
                    if other_id == str(item.id):
                        continue
                    sim = r.get("similarity", 0)
                    if sim < VECTOR_SIMILARITY_THRESHOLD:
                        continue
                    key = (str(min(str(item.id), other_id)), str(max(str(item.id), other_id)))
                    if key in seen:
                        continue
                    seen.add(key)
                    other = next((m for m in items if str(m.id) == other_id), None)
                    if not other:
                        continue
                    pairs.append(
                        DuplicatePair(
                            memory_a=self._to_pair_item(item),
                            memory_b=self._to_pair_item(other),
                            similarity=round(sim, 3),
                            reason=f"벡터 유사도 {round(sim * 100)}%",
                        )
                    )
            except Exception:
                logger.warning("중복 검색 실패: memory_id=%s", item.id, exc_info=True)

        pairs.sort(key=lambda p: p.similarity, reverse=True)
        return pairs[:20]

    async def merge_memories(self, user_id: UUID, keep_id: UUID, merge_id: UUID) -> list[str]:
        """두 메모리 병합: 태그 합집합 → keep에 반영, merge 삭제."""
        keep = await self.memory_repo.get_by_id(keep_id, user_id)
        merge = await self.memory_repo.get_by_id(merge_id, user_id)

        if not keep or not merge:
            raise ValueError("메모리를 찾을 수 없습니다")

        keep_tags = keep.tags or []
        merge_tags = merge.tags or []
        merged_tags = list(dict.fromkeys(keep_tags + merge_tags))

        await asyncio.to_thread(
            self.memory_repo._update_with_owner,
            str(keep_id),
            str(user_id),
            {"tags": merged_tags},
        )
        await self.memory_repo.delete(merge_id, user_id)

        return merged_tags

    @staticmethod
    def _to_pair_item(memory) -> DuplicatePairItem:
        return DuplicatePairItem(
            id=memory.id,
            title=memory.title,
            summary=memory.summary,
            source_type=memory.source_type,
            source_url=memory.source_url,
            tags=memory.tags,
        )
