"""애플리케이션 로깅 설정 — request_id, user_id 자동 부착.

`configure_logging()`을 main 부팅 시 한 번 호출하면 모든 logger가
`[request_id=abc123 user=...] message` 형식으로 출력된다.

uvicorn의 자체 로거(uvicorn.access)도 같은 핸들러를 공유하므로
"어떤 요청에서 무슨 일이 일어났는지" 추적 가능.
"""

from __future__ import annotations

import logging
import logging.config

from app.observability.context import RequestContextFilter

_LOG_FORMAT = "%(asctime)s [%(levelname)s] [rid=%(request_id)s user=%(user_id)s] %(name)s: %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """애플리케이션 전역 로깅 설정.

    - request_id/user_id를 모든 LogRecord에 자동 부착 (RequestContextFilter)
    - uvicorn 로거도 같은 포맷/필터를 적용해 access log에서도 rid 가시화
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": RequestContextFilter,
            },
        },
        "formatters": {
            "standard": {
                "format": _LOG_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["request_context"],
            },
        },
        "loggers": {
            "": {  # root
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": ["console"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["console"], "level": level, "propagate": False},
        },
    }
    logging.config.dictConfig(config)
