"""
Vector Repository
Data access layer for vector embeddings and similarity search using Supabase pgvector.

Embedding generation uses LangChain's native async API.
Synchronous Supabase calls are delegated to a thread via ``asyncio.to_thread``.
"""

import asyncio
from typing import Any

from langchain_openai import OpenAIEmbeddings
from supabase import Client

from app.config.settings import get_settings


class VectorRepository:
    """Repository for vector embedding operations."""

    def __init__(self, db: Client):
        self.db = db
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY,
        )

    # ------------------------------------------------------------------
    # Public async interface
    # ------------------------------------------------------------------

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a query string."""
        return await self.embeddings.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of documents."""
        return await self.embeddings.aembed_documents(texts)

    async def save_embedding(self, memory_id: str, content: str) -> None:
        """Generate embedding for memory content and save to DB."""
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
        """Search for similar memories using Supabase RPC."""
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
    # Private synchronous helpers (run in thread)
    # ------------------------------------------------------------------

    def _update_embedding(self, memory_id: str, embedding: list[float]):
        return self.db.table("memories").update({"embedding": embedding}).eq("id", memory_id).execute()

    def _rpc_match(self, rpc_params: dict):
        return self.db.rpc("match_memories", rpc_params).execute()
