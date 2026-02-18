from functools import lru_cache

from fastapi import Depends
from supabase import Client

from app.config.database import get_supabase_client

# --- Repositories ---
from app.repositories.chat_repository import ChatRepository
from app.repositories.graph_repository import GraphRepository
from app.repositories.journal_memory_link_repository import JournalMemoryLinkRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.stats_repository import StatsRepository
from app.repositories.vector_repository import VectorRepository

# --- Services ---
from app.services.chat_service import ChatService
from app.services.digest_service import DigestService
from app.services.duplicate_service import DuplicateService
from app.services.export_service import ExportService
from app.services.graph_insight_service import GraphInsightService
from app.services.graph_service import GraphService
from app.services.insight_service import InsightService
from app.services.journal_service import JournalService
from app.services.kakao_channel_service import KakaoChannelService
from app.services.memory_service import MemoryService
from app.services.search_service import SearchService
from app.services.stats_service import StatsService


# --- DB Client ---
def get_db() -> Client:
    """Supabase 클라이언트 반환."""
    return get_supabase_client()


# --- Repository Factories ---
def get_memory_repository(db: Client = Depends(get_db)) -> MemoryRepository:
    """MemoryRepository 인스턴스 생성."""
    return MemoryRepository(db)


def get_vector_repository(db: Client = Depends(get_db)) -> VectorRepository:
    """VectorRepository 인스턴스 생성."""
    return VectorRepository(db)


@lru_cache
def get_graph_repository() -> GraphRepository:
    """GraphRepository 싱글톤 반환 (KuzuDB 초기화 비용 절감)."""
    return GraphRepository()


def get_chat_repository(db: Client = Depends(get_db)) -> ChatRepository:
    """ChatRepository 인스턴스 생성."""
    return ChatRepository(db)


def get_stats_repository(db: Client = Depends(get_db)) -> StatsRepository:
    """StatsRepository 인스턴스 생성."""
    return StatsRepository(db)


def get_journal_repository(db: Client = Depends(get_db)) -> JournalRepository:
    """JournalRepository 인스턴스 생성."""
    return JournalRepository(db)


def get_journal_memory_link_repository(db: Client = Depends(get_db)) -> JournalMemoryLinkRepository:
    """JournalMemoryLinkRepository 인스턴스 생성."""
    return JournalMemoryLinkRepository(db)


# --- Service Factories ---
def get_memory_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> MemoryService:
    """MemoryService 인스턴스 생성."""
    return MemoryService(memory_repo, vector_repo, graph_repo)


def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
) -> ChatService:
    """ChatService 인스턴스 생성."""
    return ChatService(chat_repo)


def get_search_service(
    vector_repo: VectorRepository = Depends(get_vector_repository),
    memory_repo: MemoryRepository = Depends(get_memory_repository),
) -> SearchService:
    """SearchService 인스턴스 생성."""
    return SearchService(vector_repo, memory_repo)


def get_stats_service(
    stats_repo: StatsRepository = Depends(get_stats_repository),
) -> StatsService:
    """StatsService 인스턴스 생성."""
    return StatsService(stats_repo)


def get_graph_service(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    memory_repo: MemoryRepository = Depends(get_memory_repository),
) -> GraphService:
    """GraphService 인스턴스 생성."""
    return GraphService(graph_repo, memory_repo)


def get_graph_insight_service(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    stats_repo: StatsRepository = Depends(get_stats_repository),
) -> GraphInsightService:
    """GraphInsightService 인스턴스 생성."""
    return GraphInsightService(graph_repo, stats_repo)


def get_journal_service(
    journal_repo: JournalRepository = Depends(get_journal_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
    chat_repo: ChatRepository = Depends(get_chat_repository),
    link_repo: JournalMemoryLinkRepository = Depends(get_journal_memory_link_repository),
) -> JournalService:
    """JournalService 인스턴스 생성."""
    return JournalService(journal_repo, graph_repo, vector_repo, chat_repo, link_repo)


def get_digest_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    journal_repo: JournalRepository = Depends(get_journal_repository),
    chat_repo: ChatRepository = Depends(get_chat_repository),
) -> DigestService:
    """DigestService 인스턴스 생성."""
    return DigestService(memory_repo, journal_repo, chat_repo)


def get_kakao_channel_service(
    db: Client = Depends(get_db),
    memory_service: MemoryService = Depends(get_memory_service),
) -> KakaoChannelService:
    """KakaoChannelService 인스턴스 생성."""
    return KakaoChannelService(db, memory_service)


def get_export_service(
    db: Client = Depends(get_db),
) -> ExportService:
    """ExportService 인스턴스 생성."""
    return ExportService(db)


def get_insight_service(
    stats_repo: StatsRepository = Depends(get_stats_repository),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    journal_repo: JournalRepository = Depends(get_journal_repository),
) -> InsightService:
    """InsightService 인스턴스 생성."""
    return InsightService(stats_repo, graph_repo, journal_repo)


def get_duplicate_service(
    memory_repo: MemoryRepository = Depends(get_memory_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
) -> DuplicateService:
    """DuplicateService 인스턴스 생성."""
    return DuplicateService(memory_repo, vector_repo)


def get_notification_repository(
    db: Client = Depends(get_db),
) -> NotificationRepository:
    """NotificationRepository 인스턴스 생성."""
    return NotificationRepository(db)
