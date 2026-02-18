from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """환경변수 기반 애플리케이션 설정."""

    APP_NAME: str = "Memoir AI"
    DEBUG: bool = False

    FRONTEND_URL: str = "http://localhost:5173"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://memoir-ai.vercel.app",
        "https://memoir-ai-frontend.vercel.app",
        "https://frontend-three-orcin-64.vercel.app",
    ]
    ALLOWED_ORIGINS: str | None = None  # 쉼표로 구분된 프로덕션 도메인 (예: "https://memoir.fly.dev")

    OPENAI_API_KEY: str

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    KUZU_DB_PATH: str = "./kuzu_data"

    UPSTAGE_API_KEY: str | None = None

    KAKAO_SKILL_SECRET: str | None = None

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
    return Settings()
