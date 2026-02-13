import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.error_handler import register_error_handlers
from app.config.middleware import register_middleware
from app.routers.router import api_router
from app.services.scheduler_service import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """앱 시작/종료 시 스케줄러 관리."""
    start_scheduler()
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
