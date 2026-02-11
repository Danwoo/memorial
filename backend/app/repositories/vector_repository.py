import asyncio
from typing import Any

from langchain_openai import OpenAIEmbeddings
from supabase import Client

from app.config.settings import get_settings


class VectorRepository:
    """벡터 임베딩 및 유사도 검색 데이터 접근 계층 (Supabase pgvector)."""

    def __init__(self, db: Client):
        self.db = db
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )

    # ------------------------------------------------------------------
    # 공개 비동기 인터페이스
    # ------------------------------------------------------------------

    async def embed_query(self, text: str) -> list[float]:
        """쿼리 문자열의 임베딩 벡터 생성."""
        return await self.embeddings.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """문서 리스트의 임베딩 벡터 생성."""
        return await self.embeddings.aembed_documents(texts)

    async def save_embedding(self, memory_id: str, content: str) -> None:
        """Memory 콘텐츠의 임베딩을 생성하여 DB에 저장."""
        if not content:
            return

        embedding = await self.embed_query(content)
        await asyncio.to_thread(self._update_embedding, memory_id, embedding)

    async def similarity_search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.5,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Supabase RPC를 이용한 벡터 유사도 검색."""
        query_embedding = await self.embed_query(query)

        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter": filters or {},
        }

        response = await asyncio.to_thread(self._rpc_match, rpc_params)
        return response.data

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _update_embedding(self, memory_id: str, embedding: list[float]):
        return self.db.table("memories").update({"embedding": embedding}).eq("id", memory_id).execute()

    def _rpc_match(self, rpc_params: dict):
        return self.db.rpc("match_memories", rpc_params).execute()
