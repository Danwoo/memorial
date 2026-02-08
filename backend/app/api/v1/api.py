"""
API v1 Router
Aggregates all v1 endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import memory, chat, graph, search, auth, integrations, stats

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router)
api_router.include_router(memory.router)
api_router.include_router(chat.router)
api_router.include_router(graph.router)
api_router.include_router(search.router)
api_router.include_router(integrations.router)
api_router.include_router(stats.router)




