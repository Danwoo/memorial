"""
API v1 Router Aggregator
Combines all v1 routers into a single router
"""
from fastapi import APIRouter

from app.routers.v1 import auth, chat, digest, graph, integrations, journal, memory, search, stats

api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(memory.router)
api_router.include_router(chat.router)
api_router.include_router(graph.router)
api_router.include_router(search.router)
api_router.include_router(auth.router)
api_router.include_router(integrations.router)
api_router.include_router(stats.router)
api_router.include_router(journal.router)
api_router.include_router(digest.router)

