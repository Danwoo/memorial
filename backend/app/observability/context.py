"""Request-scoped 컨텍스트 — request_id, user_id 등 로그 상관관계용.

contextvars로 비동기 안전한 request-scope를 유지하며,
RequestIdMiddleware가 HTTP 진입 시 자동 채워준다.

로그 포맷터는 이 값들을 모든 LogRecord에 자동 부착(filter)하므로
호출 사이트는 별도 코드 없이 request_id가 로그에 흐른다.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

# 요청 단위로 부여되는 ID — 분산 trace의 spanID 역할
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# 인증된 사용자 ID (있을 때) — 로그 상관관계용
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")


def new_request_id() -> str:
    """짧은 request_id 생성 (UUID4의 12자)."""
    return uuid.uuid4().hex[:12]


class RequestContextFilter(logging.Filter):
    """모든 LogRecord에 request_id/user_id를 부착하는 filter.

    로그 포맷터에서 %(request_id)s, %(user_id)s를 사용할 수 있도록 한다.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True
