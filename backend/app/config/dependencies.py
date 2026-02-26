from functools import lru_cache

from fastapi import Depends
from supabase import Client

from app.config.database import get_supabase_client
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.diary_scrap_link_repository import DiaryScrapLinkRepository
from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.scrap_repository import ScrapRepository

# ─── DI 구조 설명 ──────────────────────────────────────────────────────────
# FastAPI의 Depends 시스템을 활용한 의존성 주입 컨테이너.
#
# 계층 구조:
#   DB Client (Supabase) → Repository → Service → Router
#
# 각 팩토리 함수는 FastAPI 라우터에서 Depends()로 주입됨.
# Repository는 DB 클라이언트를 받고, Service는 Repository를 받는 구조.
# MindmapRepository만 @lru_cache로 싱글톤 관리 (KuzuDB 초기화 비용 절감).
# ────────────────────────────────────────────────────────────────────────────
# --- Repositories ---
from app.repositories.socrates_repository import SocratesRepository
from app.repositories.vector_repository import VectorRepository
from app.services.calendar_service import CalendarService
from app.services.diary_analysis_service import DiaryAnalysisService
from app.services.diary_service import DiaryService
from app.services.digest_service import DigestService
from app.services.duplicate_service import DuplicateService
from app.services.export_service import ExportService
from app.services.hybrid_search_service import HybridSearchService
from app.services.insight_service import InsightService
from app.services.kakao_channel_service import KakaoChannelService
from app.services.mindmap_insight_service import MindmapInsightService
from app.services.mindmap_service import MindmapService
from app.services.report_service import ReportService
from app.services.scrap_service import ScrapService
from app.services.search_service import SearchService

# --- Services ---
from app.services.socrates_service import SocratesService


# --- DB Client ---
def get_db() -> Client:
    """Supabase 클라이언트 반환."""
    return get_supabase_client()


# --- Repository Factories ---
def get_scrap_repository(db: Client = Depends(get_db)) -> ScrapRepository:
    """ScrapRepository 인스턴스 생성."""
    return ScrapRepository(db)


def get_vector_repository(db: Client = Depends(get_db)) -> VectorRepository:
    """VectorRepository 인스턴스 생성."""
    return VectorRepository(db)


@lru_cache
def get_mindmap_repository() -> MindmapRepository:
    """MindmapRepository 싱글톤 반환 (KuzuDB 초기화 비용 절감)."""
    return MindmapRepository()


def get_socrates_repository(db: Client = Depends(get_db)) -> SocratesRepository:
    """SocratesRepository 인스턴스 생성."""
    return SocratesRepository(db)


def get_calendar_repository(db: Client = Depends(get_db)) -> CalendarRepository:
    """CalendarRepository 인스턴스 생성."""
    return CalendarRepository(db)


def get_diary_repository(db: Client = Depends(get_db)) -> DiaryRepository:
    """DiaryRepository 인스턴스 생성."""
    return DiaryRepository(db)


def get_diary_scrap_link_repository(db: Client = Depends(get_db)) -> DiaryScrapLinkRepository:
    """DiaryScrapLinkRepository 인스턴스 생성."""
    return DiaryScrapLinkRepository(db)


# --- Service Factories ---
def get_scrap_service(
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
    mindmap_repo: MindmapRepository = Depends(get_mindmap_repository),
) -> ScrapService:
    """ScrapService 인스턴스 생성."""
    return ScrapService(scrap_repo, vector_repo, mindmap_repo)


def get_socrates_service(
    socrates_repo: SocratesRepository = Depends(get_socrates_repository),
) -> SocratesService:
    """SocratesService 인스턴스 생성."""
    return SocratesService(socrates_repo)


def get_hybrid_search_service(
    vector_repo: VectorRepository = Depends(get_vector_repository),
    mindmap_repo: MindmapRepository = Depends(get_mindmap_repository),
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
) -> HybridSearchService:
    """HybridSearchService 인스턴스 생성."""
    return HybridSearchService(vector_repo, mindmap_repo, scrap_repo)


def get_search_service(
    vector_repo: VectorRepository = Depends(get_vector_repository),
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
    mindmap_repo: MindmapRepository = Depends(get_mindmap_repository),
    hybrid_search: HybridSearchService = Depends(get_hybrid_search_service),
) -> SearchService:
    """SearchService 인스턴스 생성."""
    return SearchService(vector_repo, scrap_repo, mindmap_repo, hybrid_search=hybrid_search)


def get_calendar_service(
    calendar_repo: CalendarRepository = Depends(get_calendar_repository),
) -> CalendarService:
    """CalendarService 인스턴스 생성."""
    return CalendarService(calendar_repo)


def get_mindmap_service(
    mindmap_repo: MindmapRepository = Depends(get_mindmap_repository),
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
) -> MindmapService:
    """MindmapService 인스턴스 생성."""
    return MindmapService(mindmap_repo, scrap_repo)


def get_mindmap_insight_service(
    mindmap_repo: MindmapRepository = Depends(get_mindmap_repository),
    calendar_repo: CalendarRepository = Depends(get_calendar_repository),
) -> MindmapInsightService:
    """MindmapInsightService 인스턴스 생성."""
    return MindmapInsightService(mindmap_repo, calendar_repo)


def get_diary_service(
    diary_repo: DiaryRepository = Depends(get_diary_repository),
    link_repo: DiaryScrapLinkRepository = Depends(get_diary_scrap_link_repository),
) -> DiaryService:
    """DiaryService 인스턴스 생성."""
    return DiaryService(diary_repo, link_repo)


def get_diary_analysis_service(
    socrates_repo: SocratesRepository = Depends(get_socrates_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
) -> DiaryAnalysisService:
    """DiaryAnalysisService 인스턴스 생성."""
    return DiaryAnalysisService(socrates_repo, vector_repo)


def get_digest_service(
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
    diary_repo: DiaryRepository = Depends(get_diary_repository),
    socrates_repo: SocratesRepository = Depends(get_socrates_repository),
) -> DigestService:
    """DigestService 인스턴스 생성."""
    return DigestService(scrap_repo, diary_repo, socrates_repo)


def get_kakao_channel_service(
    db: Client = Depends(get_db),
    scrap_service: ScrapService = Depends(get_scrap_service),
) -> KakaoChannelService:
    """KakaoChannelService 인스턴스 생성."""
    return KakaoChannelService(db, scrap_service)


def get_export_service(
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
    diary_repo: DiaryRepository = Depends(get_diary_repository),
    socrates_repo: SocratesRepository = Depends(get_socrates_repository),
) -> ExportService:
    """ExportService 인스턴스 생성."""
    return ExportService(scrap_repo, diary_repo, socrates_repo)


def get_insight_service(
    calendar_repo: CalendarRepository = Depends(get_calendar_repository),
    mindmap_repo: MindmapRepository = Depends(get_mindmap_repository),
    diary_repo: DiaryRepository = Depends(get_diary_repository),
) -> InsightService:
    """InsightService 인스턴스 생성."""
    return InsightService(calendar_repo, mindmap_repo, diary_repo)


def get_report_service(
    calendar_repo: CalendarRepository = Depends(get_calendar_repository),
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
) -> ReportService:
    """ReportService 인스턴스 생성."""
    return ReportService(calendar_repo, scrap_repo)


def get_duplicate_service(
    scrap_repo: ScrapRepository = Depends(get_scrap_repository),
    vector_repo: VectorRepository = Depends(get_vector_repository),
) -> DuplicateService:
    """DuplicateService 인스턴스 생성."""
    return DuplicateService(scrap_repo, vector_repo)


def get_notification_repository(
    db: Client = Depends(get_db),
) -> NotificationRepository:
    """NotificationRepository 인스턴스 생성."""
    return NotificationRepository(db)
