"""
Kakao API Service
Handles KakaoTalk "Send to Me" messaging via REST API with Supabase token persistence

Kakao OAuth Flow:
1. User clicks "Connect Kakao" -> Frontend redirects to /kakao/auth
2. Server returns Kakao OAuth URL
3. User authorizes in Kakao
4. Kakao redirects back to our callback with code
5. We exchange code for access_token
6. Store token in Supabase for sending messages
"""
import logging
from urllib.parse import urlencode

import httpx
from supabase import Client

from app.config.settings import get_settings
from app.infrastructure.database import get_supabase_client

logger = logging.getLogger(__name__)

# Kakao API endpoints
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_MESSAGE_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


class KakaoService:
    """Service for Kakao integration with Supabase persistence"""

    def __init__(self, db: Client):
        self.db = db

    def get_auth_url(self, state: str | None = None) -> str:
        """
        Generate Kakao OAuth authorization URL.

        Returns:
            str: URL to redirect user for Kakao login
        """
        settings = get_settings()

        params = {
            "client_id": settings.KAKAO_REST_API_KEY,
            "redirect_uri": settings.KAKAO_REDIRECT_URI,
            "response_type": "code",
            "scope": "talk_message"  # Required for sending messages
        }

        if state:
            params["state"] = state

        return f"{KAKAO_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str, user_id: str) -> dict:
        """
        Exchange authorization code for access token and store in Supabase.

        Args:
            code: Authorization code from Kakao callback
            user_id: User ID to associate token with

        Returns:
            dict: Token response containing access_token, refresh_token, etc.
        """
        settings = get_settings()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                KAKAO_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.KAKAO_REST_API_KEY,
                    "redirect_uri": settings.KAKAO_REDIRECT_URI,
                    "code": code
                }
            )

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Kakao token exchange failed: {error_data}")

            token_data = response.json()

            # Store token in Supabase
            await self._save_token(user_id, token_data)

            return token_data

    async def _save_token(self, user_id: str, token_data: dict) -> None:
        """Save or update token in Supabase."""
        data = {
            "user_id": user_id,
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "bearer"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope")
        }

        try:
            # Upsert - insert or update if user_id exists
            self.db.table("kakao_tokens").upsert(
                data,
                on_conflict="user_id"
            ).execute()
        except Exception:
            logger.exception("Error saving Kakao token to Supabase")
            raise

    async def get_stored_token(self, user_id: str) -> str | None:
        """Get stored access token for a user from Supabase."""
        try:
            result = self.db.table("kakao_tokens") \
                .select("access_token") \
                .eq("user_id", user_id) \
                .execute()

            if result.data and len(result.data) > 0:
                return result.data[0].get("access_token")
            return None
        except Exception:
            logger.exception("Error getting Kakao token from Supabase")
            return None

    async def delete_token(self, user_id: str) -> bool:
        """Delete stored token for a user."""
        try:
            self.db.table("kakao_tokens") \
                .delete() \
                .eq("user_id", user_id) \
                .execute()
            return True
        except Exception:
            logger.exception("Error deleting Kakao token")
            return False

    async def is_connected(self, user_id: str) -> bool:
        """Check if user has connected Kakao."""
        token = await self.get_stored_token(user_id)
        return token is not None

    async def send_message_to_me(
        self,
        access_token: str,
        text: str,
        link_title: str | None = None,
        link_url: str | None = None
    ) -> dict:
        """
        Send a message to user's "나와의 채팅" (KakaoTalk Me).

        Args:
            access_token: User's Kakao access token
            text: Message text content
            link_title: Optional button text
            link_url: Optional button URL

        Returns:
            dict: Kakao API response
        """
        import json

        # Build template object
        template_object = {
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": link_url or "https://memoir.ai",
                "mobile_web_url": link_url or "https://memoir.ai"
            }
        }

        if link_title:
            template_object["button_title"] = link_title

        async with httpx.AsyncClient() as client:
            response = await client.post(
                KAKAO_MESSAGE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={
                    "template_object": json.dumps(template_object)
                }
            )

            result = response.json()

            if response.status_code != 200:
                raise Exception(f"Kakao message send failed: {result}")

            return result

    async def send_memoir_notification(
        self,
        user_id: str,
        memory_title: str,
        memory_summary: str,
        memory_id: str | None = None
    ) -> bool:
        """
        Send a Memoir notification to user's KakaoTalk.

        Args:
            user_id: User ID to get stored token
            memory_title: Title of the memory/insight
            memory_summary: Summary text
            memory_id: Optional ID for linking back to Memoir

        Returns:
            bool: True if sent successfully
        """
        token = await self.get_stored_token(user_id)
        if not token:
            raise Exception("Kakao not connected. Please authorize first.")

        # Build message
        text = f"📚 Memoir 알림\n\n{memory_title}\n\n{memory_summary}"

        # Truncate if too long (Kakao limit ~200 chars for text template)
        if len(text) > 200:
            text = text[:197] + "..."

        settings = get_settings()
        link_url = f"{settings.FRONTEND_URL}/memories/{memory_id}" if memory_id else None

        try:
            await self.send_message_to_me(
                access_token=token,
                text=text,
                link_title="Memoir에서 보기",
                link_url=link_url
            )
            return True
        except Exception:
            logger.exception("Failed to send Kakao message")
            return False


# Legacy functions for backward compatibility
# These will use a default singleton instance

_default_service: KakaoService | None = None

def _get_default_service() -> KakaoService:
    global _default_service
    if _default_service is None:
        _default_service = KakaoService(get_supabase_client())
    return _default_service

def get_auth_url(state: str | None = None) -> str:
    """Legacy: Generate Kakao OAuth authorization URL."""
    return _get_default_service().get_auth_url(state)

async def exchange_code_for_token(code: str) -> dict:
    """Legacy: Exchange code for token (uses default_user)."""
    return await _get_default_service().exchange_code_for_token(code, "default_user")

def get_stored_token(user_id: str = "default_user") -> str | None:
    """Legacy: Sync wrapper (not recommended)."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get_default_service().get_stored_token(user_id))
    except Exception:
        logger.exception("Error in legacy get_stored_token")
        return None

async def send_memoir_notification(
    memory_title: str,
    memory_summary: str,
    memory_id: str | None = None,
    user_id: str = "default_user"
) -> bool:
    """Legacy: Send notification."""
    return await _get_default_service().send_memoir_notification(
        user_id, memory_title, memory_summary, memory_id
    )
