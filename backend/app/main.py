import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import get_supabase_client
from app.config.error_handler import register_error_handlers
from app.config.middleware import register_middleware
from app.config.settings import get_settings
from app.repositories.mindmap_repository import MindmapRepository
from app.repositories.scrap_repository import ScrapRepository
from app.routers.router import api_router
from app.services.mindmap_service import MindmapService
from app.services.scheduler_service import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """앱 시작/종료 시 스케줄러 관리 + KuzuDB 리빌드 + 에이전트 등록."""
    start_scheduler()

    # Supabase에 저장된 그래프 데이터로 KuzuDB 리빌드 (영구 디스크 없이도 그래프 복원)
    try:
        db = get_supabase_client()
        scrap_repo = ScrapRepository(db)
        mindmap_repo = MindmapRepository()
        mindmap_service = MindmapService(mindmap_repo, scrap_repo)
        result = await mindmap_service.rebuild_from_supabase()
        logger.info("KuzuDB startup rebuild: %s", result)
    except Exception:
        logger.exception("KuzuDB rebuild failed on startup (non-fatal)")

    _register_all_agents()

    yield
    stop_scheduler()


def _register_all_agents() -> None:
    """모든 에이전트를 AgentRegistry에 등록한다.

    부팅 시점에 명시적으로 호출되어야 한다. 모듈 import-side-effect로 등록하는 패턴은
    테스트 격리성을 깨기 때문에 제거되었다.
    """
    from app.agents.analyst.graph import _register_analyst
    from app.agents.curator.graph import _register_curator
    from app.agents.librarian.graph import _register_librarian
    from app.agents.oracle.graph import _register_oracle
    from app.agents.reporter.graph import _register_reporter
    from app.agents.scribe.graph import _register_scribe
    from app.agents.socrates.graph import _register_socrates
    from app.agents.supervisor.graph import _register_supervisor

    _register_socrates()
    _register_oracle()
    _register_librarian()
    _register_analyst()
    _register_scribe()
    _register_curator()
    _register_reporter()
    _register_supervisor()
    logger.info("에이전트 등록 완료")


_settings = get_settings()
app = FastAPI(
    title="Memoir AI",
    description="지능형 인지 장부 - Backend API",
    version="0.1.0",
    lifespan=lifespan,
    # 프로덕션에서 OpenAPI 문서 비활성화 (정보 노출 방지)
    docs_url="/docs" if _settings.DEBUG else None,
    redoc_url="/redoc" if _settings.DEBUG else None,
    openapi_url="/openapi.json" if _settings.DEBUG else None,
)

register_middleware(app)
register_error_handlers(app)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (인증 불필요)."""
    return {"status": "ok"}


app.include_router(api_router)
