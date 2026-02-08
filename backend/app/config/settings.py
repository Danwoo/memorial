"""
Core Configuration for Memoir AI Backend
Pydantic Settings for environment variable management
"""
from uuid import UUID

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

# Single source of truth for the development mock user ID.
# TODO: Remove once real JWT authentication is implemented.
DEFAULT_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App info
    APP_NAME: str = "Memoir AI"
    DEBUG: bool = False
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Neo4j (Optional for Phase 1)
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    
    # Upstage (PDF Parsing)
    UPSTAGE_API_KEY: Optional[str] = None
    
    # Kakao API (KakaoTalk notifications)
    KAKAO_REST_API_KEY: Optional[str] = None
    KAKAO_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/kakao/callback"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance (Singleton pattern)"""
    return Settings()
