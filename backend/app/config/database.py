"""
Supabase Client Singleton
Provides authenticated Supabase client for database operations
"""
import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client instance.
    """
    settings = get_settings()

    # Ensure configured
    if "your-project" in settings.SUPABASE_URL or not settings.SUPABASE_URL:
        logger.warning("Supabase URL not configured!")

    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase Service Role Key missing!")

    # Use service role key if available, otherwise anon key
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY

    return create_client(
        settings.SUPABASE_URL,
        key
    )

