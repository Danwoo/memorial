from fastapi import APIRouter

from app.routers import (
    auth_router,
    briefing_router,
    chat_router,
    digest_router,
    export_router,
    graph_router,
    insight_router,
    integrations_router,
    journal_router,
    memory_router,
    notification_router,
    search_router,
    stats_router,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(memory_router.router)
api_router.include_router(chat_router.router)
api_router.include_router(graph_router.router)
api_router.include_router(search_router.router)
api_router.include_router(auth_router.router)
api_router.include_router(integrations_router.router)
api_router.include_router(stats_router.router)
api_router.include_router(journal_router.router)
api_router.include_router(digest_router.router)
api_router.include_router(notification_router.router)
api_router.include_router(briefing_router.router)
api_router.include_router(insight_router.router)
api_router.include_router(export_router.router)
