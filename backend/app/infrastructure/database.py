"""
Supabase Client Singleton
Provides authenticated Supabase client for database operations
"""
from supabase import create_client, Client
from functools import lru_cache
from app.config.settings import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client instance.
    """
    settings = get_settings()
    
    # Ensure configured
    if "your-project" in settings.SUPABASE_URL or not settings.SUPABASE_URL:
        print("[WARNING] Supabase URL not configured!")
    
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("[WARNING] Supabase Service Role Key missing!")
    
    # Use service role key if available, otherwise anon key
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    
    return create_client(
        settings.SUPABASE_URL,
        key
    )


def get_supabase() -> Client:
    """Dependency injection helper for FastAPI"""
    return get_supabase_client()
