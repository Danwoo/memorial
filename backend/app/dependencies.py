"""
FastAPI Dependencies
Dependency injection configuration for repositories and services.

All repository and service factory functions live here.
Routers obtain instances exclusively via Depends(get_*).
"""
from functools import lru_cache

from fastapi import Depends
from supabase import Client

from app.infrastructure.database import get_supabase_client

# ========================================
# Repositories
# ========================================
from app.repositories.chat_repository import ChatRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.stats_repository import StatsRepository
from app.repositories.vector_repository import VectorRepository

# ========================================
# Services
# ========================================
from app.services.chat_service import ChatService
from app.services.digest_service import DigestService
from app.services.graph_service import GraphService
from app.services.journal_service import JournalService
from app.services.memory_service import MemoryService
from app.services.search_service import SearchService
from app.services.stats_service import StatsService


# ========================================
# Database Client
# ========================================
def get_db() -> Client:
    """Get Supabase client."""
    return get_supabase_client()


# ========================================
# Repository Factories
# ========================================
def get_memory_repository(db: Client = Depends(get_db)) -> MemoryRepository:
    """Get MemoryRepository instance."""
    return MemoryRepository(db)


def get_vector_repository(db: Client = Depends(get_db)) -> VectorRepository:
    """Get VectorRepository instance."""
    return VectorRepository(db)


@lru_cache
def get_graph_repository() -> GraphRepository:
    """Get GraphRepository singleton (Neo4j connection is expensive to create)."""
    return GraphRepository()


def get_chat_repository(db: Client = Depends(get_db)) -> ChatRepository:
    """Get ChatRepository instance with Supabase client."""
    return ChatRepository(db)


def get_stats_repository(db: Client = Depends(get_db)) -> StatsRepository:
    """Get StatsRepository instance."""
    return StatsRepository(db)


def get_journal_repository(db: Client = Depends(get_db)) -> JournalRepository:
    """Get JournalRepository instance."""
    return JournalRepository(db)


# ========================================
# Service Factories
# ========================================
def get_memory_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> MemoryService:
    """Get MemoryService instance with dependencies."""
    return MemoryService(memory_repo, vector_repo, graph_repo)


def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
) -> ChatService:
    """Get ChatService instance."""
    return ChatService(chat_repo)


def get_search_service(
    vector_repo: VectorRepository = Depends(get_vector_repository),
    memory_repo: MemoryRepository = Depends(get_memory_repository),
) -> SearchService:
    """Get SearchService instance."""
    return SearchService(vector_repo, memory_repo)


def get_stats_service(
    stats_repo: StatsRepository = Depends(get_stats_repository),
) -> StatsService:
    """Get StatsService instance."""
    return StatsService(stats_repo)


def get_graph_service(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    memory_repo: MemoryRepository = Depends(get_memory_repository),
) -> GraphService:
    """Get GraphService instance."""
    return GraphService(graph_repo, memory_repo)


def get_journal_service(
    journal_repo: JournalRepository = Depends(get_journal_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
) -> JournalService:
    """Get JournalService instance."""
    return JournalService(journal_repo, graph_repo, vector_repo)


def get_digest_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    journal_repo: JournalRepository = Depends(get_journal_repository),
    chat_repo: ChatRepository = Depends(get_chat_repository),
) -> DigestService:
    """Get DigestService instance."""
    return DigestService(memory_repo, journal_repo, chat_repo)


def get_kakao_service(db: Client = Depends(get_db)):
    """Get KakaoService instance."""
    from app.services.kakao_service import KakaoService
    return KakaoService(db)
