from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config.settings import get_settings

_DEFAULT_MODEL = "gpt-4o-mini"


@lru_cache
def get_creative_llm() -> ChatOpenAI:
    """창의적/대화형 작업용 ChatOpenAI 인스턴스 반환 (temperature=0.7)."""
    settings = get_settings()
    return ChatOpenAI(
        model=_DEFAULT_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
    )


@lru_cache
def get_analytical_llm() -> ChatOpenAI:
    """분석/분류 작업용 ChatOpenAI 인스턴스 반환 (temperature=0)."""
    settings = get_settings()
    return ChatOpenAI(
        model=_DEFAULT_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    )


@lru_cache
def get_streaming_llm() -> ChatOpenAI:
    """실시간 대화 스트리밍용 ChatOpenAI 인스턴스 반환."""
    settings = get_settings()
    return ChatOpenAI(
        model=_DEFAULT_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
        streaming=True,
    )
