import logging
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """FastAPI 애플리케이션에 전역 예외 핸들러 등록."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """유효성 검증 에러를 일관된 JSON 구조로 변환."""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error.get("loc", []))
            errors.append(
                {
                    "field": field,
                    "message": error.get("msg", ""),
                    "type": error.get("type", ""),
                }
            )

        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": errors,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """HTTP 예외를 일관된 JSON 구조로 변환."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """미처리 예외 캐치. 전체 traceback 로깅 후 5xx 응답."""
        logger.error(
            "Unhandled exception on %s %s\n%s",
            request.method,
            request.url.path,
            traceback.format_exc(),
        )

        settings = get_settings()
        detail = str(exc) if settings.DEBUG else "Internal server error"

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": detail,
            },
        )
