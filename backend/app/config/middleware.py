import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.rate_limit import get_user_key, rate_limiter
from app.config.settings import get_settings
from app.observability.context import new_request_id, request_id_var, user_id_var

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

# LLM 호출 경로 (10req/min)
LLM_PATHS = {
    "/api/v1/socrates/sessions/",
    "/api/v1/diaries/review-questions",
    "/api/v1/diaries/generate-draft",
    "/api/v1/diaries/insights",
    "/api/v1/reports/weekly",
    "/api/v1/reports/monthly",
    "/api/v1/scraps/backfill",
    "/api/v1/scraps/reprocess-all",
}
# 내보내기 경로 (5req/min) — DB 직렬화 + ZIP 압축으로 CPU/메모리 부하
EXPORT_PATHS = {
    "/api/v1/export/scraps",
    "/api/v1/export/diaries",
    "/api/v1/export/all",
}
# 스크랩 생성 (30req/min)
WRITE_PATHS = {"/api/v1/scraps"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """request_id를 부여하고 응답 헤더로 echo하며, contextvars에 채워 로그 상관관계 가능하게 한다.

    upstream에서 `X-Request-ID` 헤더로 trace ID를 넘기면 그대로 사용 (cross-service tracing).
    없으면 새로 생성.
    """

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and len(incoming) <= 64 else new_request_id()

        rid_token = request_id_var.set(request_id)
        uid_token = user_id_var.set("-")  # 인증 이후 라우터/dep에서 채워질 수도 있음

        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(rid_token)
            user_id_var.reset(uid_token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """경로별 레이트 리미트 미들웨어."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        try:
            key = get_user_key(request)

            # LLM 엔드포인트: 10req/min
            if method == "POST" and any(path.startswith(p) or path.endswith("/messages") for p in LLM_PATHS):
                rate_limiter.check(f"{key}:llm", max_requests=10, window_seconds=60)
            # 내보내기: 5req/min (DB 직렬화 + ZIP 압축)
            elif method == "GET" and path.rstrip("/") in EXPORT_PATHS:
                rate_limiter.check(f"{key}:export", max_requests=5, window_seconds=60)
            # 메모리 생성: 30req/min
            elif method == "POST" and path.rstrip("/") in WRITE_PATHS:
                rate_limiter.check(f"{key}:write", max_requests=30, window_seconds=60)
            # 일반 API: 120req/min
            elif path.startswith("/api/"):
                rate_limiter.check(f"{key}:general", max_requests=120, window_seconds=60)
        except Exception as exc:
            if hasattr(exc, "status_code") and exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": exc.detail},
                )
            raise

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """FastAPI 애플리케이션에 미들웨어 등록."""
    settings = get_settings()

    # ALLOWED_ORIGINS 환경변수가 설정되면 우선 적용
    if settings.ALLOWED_ORIGINS:
        origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    else:
        origins = settings.CORS_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
        max_age=600,
    )

    # 레이트 리미트 (CORS 이후 적용)
    app.add_middleware(RateLimitMiddleware)

    # 요청 컨텍스트 (가장 바깥쪽 — 모든 후속 middleware/route에서 request_id 가시화)
    app.add_middleware(RequestContextMiddleware)
