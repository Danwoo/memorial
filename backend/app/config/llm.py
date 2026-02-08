"""
LLM Provider
Shared ChatOpenAI instances for the application.

Two pre-configured profiles are available:
- ``get_creative_llm()``  -- temperature=0.7, for Socratic dialogue and reflection questions.
- ``get_analytical_llm()`` -- temperature=0, for classification and entity extraction.

Instances are cached per profile so that connection pooling and token
counting overhead are paid only once.
"""
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config.settings import get_settings

# Default model shared across all profiles.
_DEFAULT_MODEL = "gpt-4o-mini"


@lru_cache
def get_creative_llm() -> ChatOpenAI:
    """Return a cached ChatOpenAI instance tuned for creative / conversational tasks."""
    settings = get_settings()
    return ChatOpenAI(
        model=_DEFAULT_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
    )


@lru_cache
def get_analytical_llm() -> ChatOpenAI:
    """Return a cached ChatOpenAI instance tuned for deterministic / analytical tasks."""
    settings = get_settings()
    return ChatOpenAI(
        model=_DEFAULT_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    )


@lru_cache
def get_streaming_llm() -> ChatOpenAI:
    """Return a cached ChatOpenAI instance with streaming enabled for real-time dialogue."""
    settings = get_settings()
    return ChatOpenAI(
        model=_DEFAULT_MODEL,
        temperature=0.7,
        api_key=settings.OPENAI_API_KEY,
        streaming=True,
    )
