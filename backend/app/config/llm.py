from functools import lru_cache
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config.settings import get_settings

# OpenRouter 공통 설정 (프로토타입 무료 티어)
# OpenAI 크레딧 충전 후 _USE_OPENROUTER = False 로 전환
_USE_OPENROUTER = True
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_MAIN_MODEL = "upstage/solar-pro-3:free"  # 메인 LLM (한국어 특화)
_TAGGER_MODEL = "upstage/solar-pro-3:free"  # 태그 전용 (한국어 특화)
_OPENAI_MODEL = "gpt-4o-mini"  # OpenAI 직접 사용 시


def _make_gemini_llm(temperature: float, streaming: bool = False) -> ChatGoogleGenerativeAI:
    """Gemini LLM 인스턴스 생성 (OpenRouter 폴백용).

    GEMINI_LLM_MODEL 환경변수로 모델 전환 가능.
    기본값: gemini-2.0-flash
    """
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_LLM_MODEL,
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
        streaming=streaming,
    )


def _make_llm(temperature: float, streaming: bool = False) -> Any:
    """LLM 인스턴스 생성.

    GOOGLE_API_KEY 설정 시: OpenRouter → Gemini 자동 폴백 적용
    미설정 시: OpenRouter 단독 (또는 OpenAI 직접)
    """
    settings = get_settings()
    if _USE_OPENROUTER:
        primary = ChatOpenAI(
            model=_OPENROUTER_MAIN_MODEL,
            temperature=temperature,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=_OPENROUTER_BASE_URL,
            streaming=streaming,
        )
        if settings.GOOGLE_API_KEY:
            return primary.with_fallbacks([_make_gemini_llm(temperature, streaming)])
        return primary
    return ChatOpenAI(
        model=_OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        streaming=streaming,
    )


@lru_cache
def get_creative_llm() -> Any:
    """창의적/대화형 작업용 LLM 인스턴스 반환 (temperature=0.7)."""
    return _make_llm(temperature=0.7)


@lru_cache
def get_analytical_llm() -> Any:
    """분석/분류 작업용 LLM 인스턴스 반환 (temperature=0)."""
    return _make_llm(temperature=0)


@lru_cache
def get_tagger_llm() -> Any:
    """태그 추출 전용 LLM — OpenRouter upstage/solar-pro-3:free (temperature=0).

    OPENROUTER_API_KEY 미설정 시 get_analytical_llm()으로 폴백.
    GOOGLE_API_KEY 설정 시 OpenRouter 실패 시 Gemini 자동 폴백 적용.
    """
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        return get_analytical_llm()
    primary = ChatOpenAI(
        model=_TAGGER_MODEL,
        temperature=0,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=_OPENROUTER_BASE_URL,
    )
    if settings.GOOGLE_API_KEY:
        return primary.with_fallbacks([_make_gemini_llm(temperature=0)])
    return primary


@lru_cache
def get_streaming_llm() -> Any:
    """실시간 대화 스트리밍용 LLM 인스턴스 반환."""
    return _make_llm(temperature=0.7, streaming=True)
