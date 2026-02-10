"""
API v1 Router Aggregator
Combines all v1 routers into a single router
"""

from fastapi import APIRouter

from app.routers.v1 import (
    auth_router,
    chat_router,
    digest_router,
    graph_router,
    integrations_router,
    journal_router,
    memory_router,
    search_router,
    stats_router,
)

api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(memory_router.router)
api_router.include_router(chat_router.router)
api_router.include_router(graph_router.router)
api_router.include_router(search_router.router)
api_router.include_router(auth_router.router)
api_router.include_router(integrations_router.router)
api_router.include_router(stats_router.router)
api_router.include_router(journal_router.router)
api_router.include_router(digest_router.router)
