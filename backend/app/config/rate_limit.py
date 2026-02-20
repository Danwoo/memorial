import logging
from collections import defaultdict
from time import monotonic

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

MAX_RATE_LIMIT_KEYS = 10000
CLEANUP_INTERVAL_SECONDS = 300  # 5분


class RateLimiter:
    """사용자별 슬라이딩 윈도우 레이트 리미터."""

    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = monotonic()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        """요청 허용 여부 확인. 초과 시 HTTPException(429) 발생."""
        now = monotonic()

        # 주기적 만료 키 정리
        if now - self._last_cleanup > CLEANUP_INTERVAL_SECONDS:
            self._cleanup(now, window_seconds)

        cutoff = now - window_seconds
        timestamps = self._windows[key]
        self._windows[key] = [t for t in timestamps if t > cutoff]
        if len(self._windows[key]) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
            )
        self._windows[key].append(now)

    def _cleanup(self, now: float, window_seconds: int) -> None:
        """만료된 키 정리 + 크기 가드."""
        cutoff = now - window_seconds
        expired = [k for k, v in self._windows.items() if not v or v[-1] < cutoff]
        for k in expired:
            del self._windows[k]

        if len(self._windows) > MAX_RATE_LIMIT_KEYS:
            sorted_keys = sorted(self._windows, key=lambda k: self._windows[k][-1] if self._windows[k] else 0)
            for k in sorted_keys[: len(self._windows) - MAX_RATE_LIMIT_KEYS]:
                del self._windows[k]

        self._last_cleanup = now


rate_limiter = RateLimiter()


def get_user_key(request: Request) -> str:
    """요청에서 사용자 식별 키 추출 (인증 토큰 기반, 없으면 IP)."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return f"user:{auth[7:20]}"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:unknown"
