from dataclasses import dataclass

from app.repositories.diary_repository import DiaryRepository
from app.repositories.socrates_repository import SocratesRepository
from app.repositories.vector_repository import VectorRepository
from app.services.community_summary_service import CommunitySummaryService
from app.services.hybrid_search_service import HybridSearchService


@dataclass
class SocratesContext:
    """Runtime DI — LangGraph context_schema으로 노드에 주입되는 외부 의존성.

    get_agent_container() 직접 호출을 제거하고, 그래프 호출 시 ainvoke(context=ctx)로
    한 번만 조립하여 모든 노드에 주입한다.
    """

    hybrid_search: HybridSearchService
    vector_repo: VectorRepository
    diary_repo: DiaryRepository
    socrates_repo: SocratesRepository
    community_summary: CommunitySummaryService
