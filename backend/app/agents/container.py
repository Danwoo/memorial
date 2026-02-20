import logging
from dataclasses import dataclass

from app.config.database import get_supabase_client
from app.config.dependencies import get_graph_repository
from app.repositories.graph_repository import GraphRepository
from app.repositories.journal_repository import JournalRepository
from app.repositories.memory_repository import MemoryRepository
from app.repositories.vector_repository import VectorRepository
from app.services.hybrid_search_service import HybridSearchService
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


@dataclass
class AgentServiceContainer:
    """에이전트 노드에서 사용하는 서비스/리포지토리 의존성 컨테이너."""

    memory_repo: MemoryRepository
    vector_repo: VectorRepository
    journal_repo: JournalRepository
    graph_repo: GraphRepository
    hybrid_search: HybridSearchService
    memory_service: MemoryService


def get_agent_container() -> AgentServiceContainer:
    """에이전트용 서비스 컨테이너 생성. FastAPI DI 외부(LangGraph 노드)에서 사용."""
    db = get_supabase_client()
    memory_repo = MemoryRepository(db)
    vector_repo = VectorRepository(db)
    journal_repo = JournalRepository(db)
    graph_repo = get_graph_repository()
    hybrid_search = HybridSearchService(vector_repo, graph_repo, memory_repo)
    memory_service = MemoryService(memory_repo, vector_repo, graph_repo)

    return AgentServiceContainer(
        memory_repo=memory_repo,
        vector_repo=vector_repo,
        journal_repo=journal_repo,
        graph_repo=graph_repo,
        hybrid_search=hybrid_search,
        memory_service=memory_service,
    )
