"""LLM 팩토리 — provider 선택, fallback, 토큰 로깅 callback을 한 곳에 캡슐화.

모든 LLM 호출 사이트는 이 모듈의 `get_*_llm()`을 통해 인스턴스를 얻으며,
그 결과 토큰 사용량 로깅, fallback, 온도 설정이 일관되게 적용된다.
"""

from functools import lru_cache
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config.settings import get_settings
from app.observability.llm_callback import TokenUsageLogger

# OpenRouter 공통 설정 (프로토타입 무료 티어)
# OpenAI 크레딧 충전 후 _USE_OPENROUTER = False 로 전환
_USE_OPENROUTER = True
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_MAIN_MODEL = "upstage/solar-pro-3:free"  # 메인 LLM (한국어 특화)
_TAGGER_MODEL = "upstage/solar-pro-3:free"  # 태그 전용 (한국어 특화)
_OPENAI_MODEL = "gpt-4o-mini"  # OpenAI 직접 사용 시


def _make_gemini_llm(temperature: float, streaming: bool = False) -> ChatGoogleGenerativeAI:
    """Gemini LLM 인스턴스 생성 (OpenRouter 폴백용)."""
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_LLM_MODEL,
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
        streaming=streaming,
    )


def _make_llm(temperature: float, streaming: bool = False, label: str = "llm") -> Any:
    """LLM 인스턴스 생성 (callback handler로 토큰 사용량 자동 로깅).

    GOOGLE_API_KEY 설정 시: OpenRouter → Gemini 자동 폴백 적용
    미설정 시: OpenRouter 단독 (또는 OpenAI 직접)
    """
    settings = get_settings()
    callbacks = [TokenUsageLogger(label=label)]

    if _USE_OPENROUTER:
        primary = ChatOpenAI(
            model=_OPENROUTER_MAIN_MODEL,
            temperature=temperature,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=_OPENROUTER_BASE_URL,
            streaming=streaming,
            callbacks=callbacks,
        )
        if settings.GOOGLE_API_KEY:
            fallback = _make_gemini_llm(temperature, streaming)
            # callback은 primary에 등록됨 — fallback은 별도 callback 추가
            fallback.callbacks = callbacks
            return primary.with_fallbacks([fallback])
        return primary
    return ChatOpenAI(
        model=_OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        streaming=streaming,
        callbacks=callbacks,
    )


@lru_cache
def get_creative_llm() -> Any:
    """창의적/대화형 작업용 LLM 인스턴스 반환 (temperature=0.7)."""
    return _make_llm(temperature=0.7, label="creative")


@lru_cache
def get_analytical_llm() -> Any:
    """분석/분류 작업용 LLM 인스턴스 반환 (temperature=0)."""
    return _make_llm(temperature=0, label="analytical")


@lru_cache
def get_tagger_llm() -> Any:
    """태그 추출 전용 LLM — OpenRouter upstage/solar-pro-3:free (temperature=0).

    OPENROUTER_API_KEY 미설정 시 get_analytical_llm()으로 폴백.
    GOOGLE_API_KEY 설정 시 OpenRouter 실패 시 Gemini 자동 폴백 적용.
    """
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        return get_analytical_llm()

    callbacks = [TokenUsageLogger(label="tagger")]
    primary = ChatOpenAI(
        model=_TAGGER_MODEL,
        temperature=0,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=_OPENROUTER_BASE_URL,
        callbacks=callbacks,
    )
    if settings.GOOGLE_API_KEY:
        fallback = _make_gemini_llm(temperature=0)
        fallback.callbacks = callbacks
        return primary.with_fallbacks([fallback])
    return primary


@lru_cache
def get_streaming_llm() -> Any:
    """실시간 대화 스트리밍용 LLM 인스턴스 반환."""
    return _make_llm(temperature=0.7, streaming=True, label="streaming")
