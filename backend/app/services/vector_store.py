"""
Vector Store Service
Handles embedding generation and similarity search using Supabase pgvector.
"""
from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from app.core.config import get_settings
from app.core.supabase import get_supabase_client

class VectorStore:
    def __init__(self):
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        self.db = get_supabase_client()

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query string."""
        return await self.embeddings.aembed_query(text)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents."""
        return await self.embeddings.aembed_documents(texts)

    async def save_embedding(self, memory_id: str, content: str):
        """
        Generate embedding for memory content and save to DB.
        """
        if not content:
            return
            
        # Generate embedding
        embedding = await self.embed_query(content)
        
        # Update memory record with embedding
        # Using execute() to run the query
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
        """
        Search for similar memories using Supabase RPC.
        """
        # Generate query embedding
        query_embedding = await self.embed_query(query)
        
        # Prepare RPC params
        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter": filters or {}
        }
        
        # Call RPC function
        response = self.db.rpc("match_memories", rpc_params).execute()
        
        return response.data

# Singleton instance
vector_store = VectorStore()
