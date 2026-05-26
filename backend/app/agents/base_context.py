from dataclasses import dataclass

from app.repositories.diary_repository import DiaryRepository
from app.repositories.protocols.chat_repository_protocol import ChatRepositoryProtocol
from app.repositories.vector_repository import VectorRepository
from app.services.community_summary_service import CommunitySummaryService
from app.services.graphrag_retrieval_service import GraphRAGRetrievalService
from app.services.hybrid_search_service import HybridSearchService


@dataclass
class AgentContext:
    """모든 채팅 에이전트가 공유하는 Runtime DI 기반 컨텍스트.

    LangGraph context_schema=AgentContext로 주입되며
    Socrates, Librarian, Oracle 에이전트가 모두 이 컨텍스트를 사용한다.

    chat_repo는 Protocol 의존(의존성 역전) — 테스트 시 fake를 주입할 수 있다.
    """

    hybrid_search: HybridSearchService
    vector_repo: VectorRepository
    diary_repo: DiaryRepository
    chat_repo: ChatRepositoryProtocol
    community_summary: CommunitySummaryService
    graphrag_retrieval: GraphRAGRetrievalService
