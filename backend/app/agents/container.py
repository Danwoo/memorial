import logging
from dataclasses import dataclass

from app.config.database import get_supabase_client
from app.repositories.diary_repository import DiaryRepository
from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.vector_repository import VectorRepository
from app.services.community_summary_service import CommunitySummaryService
from app.services.hybrid_search_service import HybridSearchService
from app.services.scrap_service import ScrapService

logger = logging.getLogger(__name__)


@dataclass
class AgentServiceContainer:
    """에이전트 노드에서 사용하는 서비스/리포지토리 의존성 컨테이너."""

    scrap_repo: ScrapRepository
    vector_repo: VectorRepository
    diary_repo: DiaryRepository
    mindmap_repo: MindmapRepository
    hybrid_search: HybridSearchService
    scrap_service: ScrapService
    community_summary: CommunitySummaryService


def get_agent_container() -> AgentServiceContainer:
    """에이전트용 서비스 컨테이너 생성. FastAPI DI 외부(LangGraph 노드)에서 사용."""
    db = get_supabase_client()
    scrap_repo = ScrapRepository(db)
    vector_repo = VectorRepository(db)
    diary_repo = DiaryRepository(db)
    # 순환 import 방지: dependencies.py가 아닌 직접 lazy import
    from app.config.dependencies import get_mindmap_repository

    mindmap_repo = get_mindmap_repository()
    hybrid_search = HybridSearchService(vector_repo, mindmap_repo, scrap_repo)
    scrap_service = ScrapService(scrap_repo, vector_repo, mindmap_repo)
    community_summary = CommunitySummaryService(mindmap_repo)

    return AgentServiceContainer(
        scrap_repo=scrap_repo,
        vector_repo=vector_repo,
        diary_repo=diary_repo,
        mindmap_repo=mindmap_repo,
        hybrid_search=hybrid_search,
        scrap_service=scrap_service,
        community_summary=community_summary,
    )
