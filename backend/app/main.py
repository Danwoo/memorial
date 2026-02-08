"""
Memoir AI - FastAPI Application Entry Point
"""
import logging
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.routers.v1.router import api_router

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Memoir AI",
    description="지능형 인지 장부 - Backend API",
    version="0.1.0",
)

# CORS middleware (origins from settings, wildcard fallback in DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


# ========================================
# Global Exception Handlers
# ========================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format validation errors into a consistent JSON structure."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        errors.append({
            "field": field,
            "message": error.get("msg", ""),
            "type": error.get("type", ""),
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Format HTTP exceptions into a consistent JSON structure."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled exceptions. Logs full traceback for 5xx errors."""
    logger.error(
        "Unhandled exception on %s %s\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )

    detail = str(exc) if settings.DEBUG else "Internal server error"

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": detail,
        },
    )


# ========================================
# Routes
# ========================================


@app.get("/health")
async def health_check():
    """Public health check endpoint (no auth required)."""
    return {"status": "ok"}


app.include_router(api_router)
