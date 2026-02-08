"""
FastAPI Dependencies
Dependency injection configuration for repositories and services
"""
from functools import lru_cache
from fastapi import Depends
from supabase import Client

from app.infrastructure.database import get_supabase_client
from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.stats_repository import StatsRepository
from app.services.memory_service import MemoryService
from app.services.chat_service import ChatService
from app.services.search_service import SearchService
from app.services.stats_service import StatsService
from app.services.graph_service import GraphService


# ========================================
# Database Client
# ========================================
def get_db() -> Client:
    """Get Supabase client."""
    return get_supabase_client()


# ========================================
# Repositories (using Depends for proper DI chain)
# ========================================
def get_memory_repository(db: Client = Depends(get_db)) -> MemoryRepository:
    """Get MemoryRepository instance."""
    return MemoryRepository(db)


def get_vector_repository(db: Client = Depends(get_db)) -> VectorRepository:
    """Get VectorRepository instance."""
    return VectorRepository(db)


@lru_cache()
def get_graph_repository() -> GraphRepository:
    """Get GraphRepository singleton instance."""
    return GraphRepository()


def get_chat_repository(db: Client = Depends(get_db)) -> ChatRepository:
    """Get ChatRepository instance with Supabase client."""
    return ChatRepository(db)


def get_stats_repository(db: Client = Depends(get_db)) -> StatsRepository:
    """Get StatsRepository instance."""
    return StatsRepository(db)


# ========================================
# Services (using Depends for proper DI chain)
# ========================================
def get_memory_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository)
) -> MemoryService:
    """Get MemoryService instance with dependencies."""
    return MemoryService(memory_repo, vector_repo, graph_repo)


def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository)
) -> ChatService:
    """Get ChatService instance."""
    return ChatService(chat_repo)


def get_search_service(
    vector_repo: VectorRepository = Depends(get_vector_repository),
    memory_repo: MemoryRepository = Depends(get_memory_repository)
) -> SearchService:
    """Get SearchService instance."""
    return SearchService(vector_repo, memory_repo)


def get_stats_service(
    stats_repo: StatsRepository = Depends(get_stats_repository)
) -> StatsService:
    """Get StatsService instance."""
    return StatsService(stats_repo)


def get_graph_service(
    graph_repo: GraphRepository = Depends(get_graph_repository)
) -> GraphService:
    """Get GraphService instance."""
    return GraphService(graph_repo)


# ========================================
# Journal Dependencies
# ========================================
from app.repositories.journal_repository import JournalRepository
from app.services.journal_service import JournalService

def get_journal_repository() -> JournalRepository:
    """Get JournalRepository instance."""
    return JournalRepository()

def get_journal_service(
    journal_repo: JournalRepository = Depends(get_journal_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository)
) -> JournalService:
    """Get JournalService instance."""
    return JournalService(journal_repo, graph_repo)


# ========================================
# Digest Dependencies
# ========================================
from app.services.digest_service import DigestService

def get_digest_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    journal_repo: JournalRepository = Depends(get_journal_repository),
    chat_repo: ChatRepository = Depends(get_chat_repository)
) -> DigestService:
    """Get DigestService instance."""
    return DigestService(memory_repo, journal_repo, chat_repo)

