from dataclasses import dataclass

from app.repositories.diary_repository import DiaryRepository
from app.repositories.socrates_repository import SocratesRepository
from app.repositories.vector_repository import VectorRepository
from app.services.community_summary_service import CommunitySummaryService
from app.services.hybrid_search_service import HybridSearchService


@dataclass
class AgentContext:
    """모든 채팅 에이전트가 공유하는 Runtime DI 기반 컨텍스트.

    LangGraph context_schema=AgentContext로 주입되며
    Socrates, Librarian, Oracle 에이전트가 모두 이 컨텍스트를 사용한다.
    """

    hybrid_search: HybridSearchService
    vector_repo: VectorRepository
    diary_repo: DiaryRepository
    socrates_repo: SocratesRepository
    community_summary: CommunitySummaryService
