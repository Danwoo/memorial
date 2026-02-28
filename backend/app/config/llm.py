from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config.settings import get_settings

# OpenRouter 공통 설정 (프로토타입 무료 티어)
# OpenAI 크레딧 충전 후 _USE_OPENROUTER = False 로 전환
_USE_OPENROUTER = True
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_MAIN_MODEL = "upstage/solar-pro-3:free"  # 메인 LLM (한국어 특화, 현재 작동 모델)
_TAGGER_MODEL = "upstage/solar-pro-3:free"  # 태그 전용 (한국어 특화)
_OPENAI_MODEL = "gpt-4o-mini"  # OpenAI 직접 사용 시


def _make_llm(temperature: float, streaming: bool = False) -> ChatOpenAI:
    """OpenRouter 또는 OpenAI LLM 인스턴스 생성 헬퍼."""
    settings = get_settings()
    if _USE_OPENROUTER:
        return ChatOpenAI(
            model=_OPENROUTER_MAIN_MODEL,
            temperature=temperature,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=_OPENROUTER_BASE_URL,
            streaming=streaming,
        )
    return ChatOpenAI(
        model=_OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        streaming=streaming,
    )


@lru_cache
def get_creative_llm() -> ChatOpenAI:
    """창의적/대화형 작업용 ChatOpenAI 인스턴스 반환 (temperature=0.7)."""
    return _make_llm(temperature=0.7)


@lru_cache
def get_analytical_llm() -> ChatOpenAI:
    """분석/분류 작업용 ChatOpenAI 인스턴스 반환 (temperature=0)."""
    return _make_llm(temperature=0)


@lru_cache
def get_tagger_llm() -> ChatOpenAI:
    """태그 추출 전용 LLM — OpenRouter upstage/solar-pro-3:free (temperature=0).

    OPENROUTER_API_KEY 미설정 시 get_analytical_llm()으로 폴백.
    """
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        return get_analytical_llm()
    return ChatOpenAI(
        model=_TAGGER_MODEL,
        temperature=0,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=_OPENROUTER_BASE_URL,
    )


@lru_cache
def get_streaming_llm() -> ChatOpenAI:
    """실시간 대화 스트리밍용 ChatOpenAI 인스턴스 반환."""
    return _make_llm(temperature=0.7, streaming=True)
