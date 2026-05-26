"""VectorRepository 인터페이스 (의존성 역전).

벡터 임베딩 생성/저장 + 유사도/희소 검색 추상화.
Service 계층이 이 Protocol에만 의존하여 구체 구현(Supabase RPC)을 모른다.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorRepositoryProtocol(Protocol):
    """벡터 임베딩 저장/검색 인터페이스."""

    async def embed_query(self, text: str) -> list[float] | None: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def save_embedding(self, scrap_id: str, content: str) -> None: ...

    async def similarity_search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.5,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]: ...

    async def sparse_search(
        self,
        query_tokens: str,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...
