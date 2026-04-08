import logging
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """환경변수 기반 애플리케이션 설정."""

    APP_NAME: str = "Memoir AI"
    DEBUG: bool = False

    FRONTEND_URL: str = "http://localhost:5173"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://memoir-knowledge.vercel.app",
        "https://frontend-three-orcin-64.vercel.app",
    ]
    ALLOWED_ORIGINS: str | None = None  # 쉼표로 구분된 프로덕션 도메인 (예: "https://memoir.fly.dev")

    EMBEDDING_PROVIDER: str = "gemini"  # "gemini" | "openai"
    GEMINI_LLM_MODEL: str = "gemini-2.5-pro"  # Gemini LLM 폴백 모델명 (OpenRouter 장애 시 사용)
    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_JWT_SECRET: str | None = None

    KUZU_DB_PATH: str = "./kuzu_data/graph"

    UPSTAGE_API_KEY: str | None = None

    KAKAO_REST_API_KEY: str | None = None
    KAKAO_REDIRECT_URI: str | None = None
    KAKAO_SKILL_SECRET: str | None = None

    UPSTASH_REDIS_REST_URL: str | None = None
    UPSTASH_REDIS_REST_TOKEN: str | None = None

    VAPID_PUBLIC_KEY: str | None = None
    VAPID_PRIVATE_KEY: str | None = None
    VAPID_MAILTO: str = "mailto:noreply@memoir.ai"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """캐시된 Settings 싱글톤 인스턴스 반환."""
    settings = Settings()
    # 프로덕션 권고 경고
    if not settings.SUPABASE_JWT_SECRET:
        logger.warning(
            "SUPABASE_JWT_SECRET 미설정: JWT 검증이 Supabase HTTP 폴백으로 동작합니다. "
            "Supabase 대시보드 → Settings → API → JWT Secret을 .env에 추가하세요."
        )
    if settings.DEBUG:
        logger.warning("DEBUG 모드가 활성화되어 있습니다. 프로덕션에서는 DEBUG=false로 설정하세요.")
    return settings
