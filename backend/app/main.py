from fastapi import FastAPI

from app.config.error_handler import register_error_handlers
from app.config.middleware import register_middleware
from app.routers.router import api_router

app = FastAPI(
    title="Memoir AI",
    description="지능형 인지 장부 - Backend API",
    version="0.1.0",
)

register_middleware(app)
register_error_handlers(app)


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트 (인증 불필요)."""
    return {"status": "ok"}


app.include_router(api_router)
