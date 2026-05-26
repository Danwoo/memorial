import logging
from dataclasses import dataclass

from app.config.database import get_supabase_client
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.protocols.calendar_repository_protocol import CalendarRepositoryProtocol
from app.repositories.protocols.chat_repository_protocol import ChatRepositoryProtocol
from app.repositories.protocols.diary_repository_protocol import DiaryRepositoryProtocol
from app.repositories.protocols.mindmap_repository_protocol import MindmapRepositoryProtocol
from app.repositories.protocols.scrap_repository_protocol import ScrapRepositoryProtocol
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.vector_repository import VectorRepository
from app.services.community_summary_service import CommunitySummaryService
from app.services.graphrag_retrieval_service import GraphRAGRetrievalService
from app.services.hybrid_search_service import HybridSearchService
from app.services.scrap_service import ScrapService

logger = logging.getLogger(__name__)


@dataclass
class AgentServiceContainer:
    """에이전트 노드에서 사용하는 서비스/리포지토리 의존성 컨테이너.

    Repository 필드는 모두 Protocol 의존(의존성 역전).
    구현체는 get_agent_container 내부에서 결정.
    """

    scrap_repo: ScrapRepositoryProtocol
    vector_repo: VectorRepository
    diary_repo: DiaryRepositoryProtocol
    mindmap_repo: MindmapRepositoryProtocol
    calendar_repo: CalendarRepositoryProtocol
    hybrid_search: HybridSearchService
    scrap_service: ScrapService
    community_summary: CommunitySummaryService
    chat_repo: ChatRepositoryProtocol
    graphrag_retrieval: GraphRAGRetrievalService


def get_agent_container() -> AgentServiceContainer:
    """에이전트용 서비스 컨테이너 생성. FastAPI DI 외부(LangGraph 노드)에서 사용."""
    db = get_supabase_client()
    scrap_repo = ScrapRepository(db)
    vector_repo = VectorRepository(db)
    diary_repo = DiaryRepository(db)
    chat_repo = ChatRepository(db)
    calendar_repo = CalendarRepository(db)
    # 순환 import 방지: dependencies.py가 아닌 직접 lazy import
    from app.config.dependencies import get_mindmap_repository

    mindmap_repo = get_mindmap_repository()
    hybrid_search = HybridSearchService(vector_repo, mindmap_repo, scrap_repo)
    scrap_service = ScrapService(scrap_repo, vector_repo, mindmap_repo)
    community_summary = CommunitySummaryService(mindmap_repo, db)
    graphrag_retrieval = GraphRAGRetrievalService(mindmap_repo, vector_repo, db)

    return AgentServiceContainer(
        scrap_repo=scrap_repo,
        vector_repo=vector_repo,
        diary_repo=diary_repo,
        mindmap_repo=mindmap_repo,
        calendar_repo=calendar_repo,
        hybrid_search=hybrid_search,
        scrap_service=scrap_service,
        community_summary=community_summary,
        chat_repo=chat_repo,
        graphrag_retrieval=graphrag_retrieval,
    )
