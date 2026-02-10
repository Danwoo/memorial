"""
Core Configuration for Memoir AI Backend
Pydantic Settings for environment variable management
"""

from functools import lru_cache
from uuid import UUID

from pydantic_settings import BaseSettings

# Single source of truth for the development mock user ID.
# Used by the DEBUG auth bypass when no JWT token is provided.
DEFAULT_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")


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

    # Neo4j (Optional for Phase 1)
    NEO4J_URI: str | None = None
    NEO4J_USER: str | None = None
    NEO4J_PASSWORD: str | None = None

    # Upstage (PDF Parsing)
    UPSTAGE_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (Singleton pattern)."""
    return Settings()
