import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.database import get_supabase_client
from app.config.error_handler import register_error_handlers
from app.config.middleware import register_middleware
from app.repositories.graph_repository import GraphRepository
from app.repositories.memory_repository import MemoryRepository
from app.routers.router import api_router
from app.services.graph_service import GraphService
from app.services.scheduler_service import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """앱 시작/종료 시 스케줄러 관리 + KuzuDB 리빌드."""
    start_scheduler()

    # Supabase에 저장된 그래프 데이터로 KuzuDB 리빌드 (영구 디스크 없이도 그래프 복원)
    try:
        db = get_supabase_client()
        memory_repo = MemoryRepository(db)
        graph_repo = GraphRepository()
        graph_service = GraphService(graph_repo, memory_repo)
        result = await graph_service.rebuild_from_supabase()
        logger.info("KuzuDB startup rebuild: %s", result)
    except Exception:
        logger.exception("KuzuDB rebuild failed on startup (non-fatal)")

    yield
    stop_scheduler()


app = FastAPI(
    title="Memoir AI",
    description="지능형 인지 장부 - Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

register_middleware(app)
register_error_handlers(app)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (인증 불필요)."""
    return {"status": "ok"}


app.include_router(api_router)
