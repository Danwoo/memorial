import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_client() -> Client:
    """캐시된 Supabase 클라이언트 싱글톤 반환."""
    settings = get_settings()

    if "your-project" in settings.SUPABASE_URL or not settings.SUPABASE_URL:
        logger.warning("Supabase URL not configured!")

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase Service Role Key missing!")

    # service role key 우선, 없으면 anon key 사용
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY

    return create_client(settings.SUPABASE_URL, key)
