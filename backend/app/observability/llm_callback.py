"""LLM 호출 관찰성(observability) — 토큰 사용량 로깅.

모든 `_make_llm()` 팩토리가 이 callback을 자동 등록하므로,
구체 호출 사이트는 별도 코드 없이 토큰 사용량이 INFO 로그로 흐른다.

LangSmith/Helicone 같은 외부 트레이서 연동도 같은 자리에 추가하면 된다.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class TokenUsageLogger(BaseCallbackHandler):
    """LLM 응답의 usage_metadata를 INFO 로그로 흘려보낸다.

    LangChain 표준 callback이며 sync/async 양쪽에서 호출된다.
    """

    def __init__(self, label: str = "llm"):
        """
        Args:
            label: 로그에 함께 출력할 식별자 (예: "creative", "analytical", "streaming")
        """
        super().__init__()
        self.label = label

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for generation_list in response.generations:
            for gen in generation_list:
                msg = getattr(gen, "message", None)
                usage: dict | None = getattr(msg, "usage_metadata", None) if msg is not None else None
                if not usage:
                    continue
                logger.info(
                    "[%s] tokens input=%s output=%s total=%s",
                    self.label,
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("total_tokens"),
                )

    # async 버전은 동일 동작 (LangChain이 자동 위임)
    async def on_llm_end_async(self, response: LLMResult, **kwargs: Any) -> None:
        self.on_llm_end(response, **kwargs)
