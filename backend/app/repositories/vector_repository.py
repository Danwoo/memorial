"""
Vector Repository
Data access layer for vector embeddings and similarity search using Supabase pgvector
"""
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from supabase import Client

from app.config.settings import get_settings


class VectorRepository:
    """Repository for vector embedding operations"""
    
    def __init__(self, db: Client):
        self.db = db
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
    
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query string."""
        return await self.embeddings.aembed_query(text)
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents."""
        return await self.embeddings.aembed_documents(texts)
    
    async def save_embedding(self, memory_id: str, content: str) -> None:
        """Generate embedding for memory content and save to DB."""
        if not content:
            return
        
        embedding = await self.embed_query(content)
        
        self.db.table("memories").update({
            "embedding": embedding
        }).eq("id", memory_id).execute()
    
    async def similarity_search(
        self, 
        query: str, 
        limit: int = 5, 
        threshold: float = 0.5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar memories using Supabase RPC."""
        query_embedding = await self.embed_query(query)
        
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter": filters or {}
        }
        
        response = self.db.rpc("match_memories", rpc_params).execute()
        return response.data
