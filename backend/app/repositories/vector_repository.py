import asyncio
import logging
from typing import Any

from supabase import Client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class VectorRepository:
    """벡터 임베딩 및 유사도 검색 데이터 접근 계층 (Supabase pgvector)."""

    def __init__(self, db: Client):
        self.db = db
        settings = get_settings()
        self.embeddings = self._init_embeddings(settings)

    def _init_embeddings(self, settings):
        """EMBEDDING_PROVIDER 환경변수에 따라 임베딩 모델 초기화."""
        provider = settings.EMBEDDING_PROVIDER.lower()

        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY 미설정 — 임베딩 비활성화")
                return None
            from langchain_openai import OpenAIEmbeddings

            logger.info("임베딩 프로바이더: OpenAI (text-embedding-3-small)")
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.OPENAI_API_KEY,
            )

        elif provider == "gemini":
            if not settings.GOOGLE_API_KEY:
                logger.warning("GOOGLE_API_KEY 미설정 — 임베딩 비활성화")
                return None
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            logger.info("임베딩 프로바이더: Gemini (gemini-embedding-001, dim=1536)")
            return GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                output_dimensionality=1536,  # OpenAI와 동일 차원 → DB 호환
                google_api_key=settings.GOOGLE_API_KEY,
            )

        else:
            logger.warning("알 수 없는 EMBEDDING_PROVIDER=%r — 임베딩 비활성화", provider)
            return None

    # ------------------------------------------------------------------
    # 공개 비동기 인터페이스
    # ------------------------------------------------------------------

    async def embed_query(self, text: str) -> list[float] | None:
        """쿼리 문자열의 임베딩 벡터 생성. 임베딩 비활성화 시 None 반환."""
        if self.embeddings is None:
            return None
        return await self.embeddings.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """문서 리스트의 임베딩 벡터 생성. 임베딩 비활성화 시 빈 리스트 반환."""
        if self.embeddings is None:
            return []
        return await self.embeddings.aembed_documents(texts)

    async def save_embedding(self, scrap_id: str, content: str) -> None:
        """Scrap 콘텐츠의 임베딩을 생성하여 DB에 저장. API 실패 시 로깅만."""
        if not content:
            return
        if self.embeddings is None:
            logger.debug("임베딩 비활성화 — scrap_id=%s 스킵", scrap_id)
            return

        try:
            embedding = await self.embed_query(content)
            if embedding is not None:
                await asyncio.to_thread(self._update_embedding, scrap_id, embedding)
        except Exception as e:
            logger.error("임베딩 저장 실패 (scrap_id=%s): %s", scrap_id, e)

    async def similarity_search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = 0.5,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Supabase RPC를 이용한 벡터 유사도 검색. 임베딩 비활성화 시 빈 결과 반환."""
        if self.embeddings is None:
            logger.debug("임베딩 비활성화 — dense search 스킵, sparse fallback 사용")
            return []

        query_embedding = await self.embed_query(query)
        if query_embedding is None:
            return []

        rpc_params = {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": limit,
            "filter": filters or {},
        }

        response = await asyncio.to_thread(self._rpc_match, rpc_params)
        results = response.data or []
        logger.debug("Dense search 결과: %d건 (threshold=%.2f)", len(results), threshold)
        return results

    async def sparse_search(
        self,
        query_tokens: str,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """tsvector 기반 키워드 검색. kiwipiepy 토큰화된 문자열을 입력받는다."""
        if not query_tokens or not query_tokens.strip():
            return []

        rpc_params = {
            "query_tokens": query_tokens,
            "p_user_id": user_id,
            "match_count": limit,
        }
        response = await asyncio.to_thread(self._rpc_sparse, rpc_params)
        return response.data if response.data else []

    # ------------------------------------------------------------------
    # 동기 헬퍼 (스레드에서 실행)
    # ------------------------------------------------------------------

    def _update_embedding(self, scrap_id: str, embedding: list[float]):
        return self.db.table("scraps").update({"embedding": embedding}).eq("id", scrap_id).execute()

    def _rpc_match(self, rpc_params: dict):
        return self.db.rpc("match_scraps", rpc_params).execute()

    def _rpc_sparse(self, rpc_params: dict):
        return self.db.rpc("sparse_search", rpc_params).execute()
