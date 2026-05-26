from fastapi import APIRouter

from app.routers import (
    auth_router,
    briefing_router,
    calendar_router,
    chat_router,
    diary_router,
    digest_router,
    duplicate_router,
    export_router,
    insight_router,
    integrations_router,
    mindmap_router,
    notification_router,
    report_router,
    scrap_router,
    search_router,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(duplicate_router.router)
api_router.include_router(scrap_router.router)
api_router.include_router(chat_router.router)
api_router.include_router(mindmap_router.router)
api_router.include_router(search_router.router)
api_router.include_router(auth_router.router)
api_router.include_router(integrations_router.router)
api_router.include_router(calendar_router.router)
api_router.include_router(diary_router.router)
api_router.include_router(digest_router.router)
api_router.include_router(notification_router.router)
api_router.include_router(briefing_router.router)
api_router.include_router(insight_router.router)
api_router.include_router(export_router.router)
api_router.include_router(report_router.router)
