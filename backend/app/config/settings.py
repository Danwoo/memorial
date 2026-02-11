"""
Core Configuration for Memoir AI Backend
Pydantic Settings for environment variable management
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App info
    APP_NAME: str = "Memoir AI"
    DEBUG: bool = False

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # OpenAI
    OPENAI_API_KEY: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    # KuzuDB (Embedded Graph Database)
    KUZU_DB_PATH: str = "./kuzu_data"

    # Upstage (PDF Parsing)
    UPSTAGE_API_KEY: str | None = None

    # Kakao OpenBuilder
    KAKAO_SKILL_SECRET: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (Singleton pattern)."""
    return Settings()
