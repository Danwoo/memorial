"""
Kakao API Service
Handles KakaoTalk "Send to Me" messaging via REST API with Supabase token persistence

Kakao OAuth Flow:
1. User clicks "Connect Kakao" -> Frontend redirects to /kakao/auth
2. Server returns Kakao OAuth URL (with user_id in state param)
3. User authorizes in Kakao
4. Kakao redirects back to our callback with code + state(user_id)
5. We exchange code for access_token
6. Store token in Supabase for sending messages
"""

import asyncio
import logging
import time
from urllib.parse import urlencode

import httpx
from supabase import Client

from app.config.settings import get_settings

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
            "scope": "talk_message",  # Required for sending messages
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
                    "code": code,
                },
            )

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(f"Kakao token exchange failed: {error_data}")

            token_data = response.json()

            # Store token in Supabase
            await self._save_token(user_id, token_data)

            return token_data

    def _sync_save_token(self, user_id: str, token_data: dict) -> None:
        """Synchronous token save (runs in thread)."""
        expires_in = token_data.get("expires_in", 21600)
        data = {
            "user_id": user_id,
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "bearer"),
            "expires_in": expires_in,
            "expires_at": int(time.time()) + expires_in,
            "scope": token_data.get("scope"),
        }
        self.db.table("kakao_tokens").upsert(data, on_conflict="user_id").execute()

    async def _save_token(self, user_id: str, token_data: dict) -> None:
        """Save or update token in Supabase."""
        try:
            await asyncio.to_thread(self._sync_save_token, user_id, token_data)
        except Exception:
            logger.exception("Error saving Kakao token to Supabase")
            raise

    async def _refresh_token(self, user_id: str, refresh_token: str) -> str | None:
        """Refresh an expired Kakao access token."""
        settings = get_settings()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                KAKAO_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.KAKAO_REST_API_KEY,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                logger.error("Kakao token refresh failed: %s", response.text)
                return None

            token_data = response.json()
            # Kakao may or may not return a new refresh_token
            if "refresh_token" not in token_data:
                token_data["refresh_token"] = refresh_token
            await self._save_token(user_id, token_data)
            return token_data.get("access_token")

    def _sync_get_token_row(self, user_id: str) -> dict | None:
        """Synchronous token fetch (runs in thread)."""
        result = (
            self.db.table("kakao_tokens")
            .select("access_token, refresh_token, expires_at")
            .eq("user_id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None

    async def get_stored_token(self, user_id: str) -> str | None:
        """Get stored access token for a user, refreshing if expired."""
        try:
            row = await asyncio.to_thread(self._sync_get_token_row, user_id)
            if not row:
                return None

            access_token = row.get("access_token")
            refresh_token = row.get("refresh_token")
            expires_at = row.get("expires_at", 0)

            # Check if token is expired (with 5 min buffer)
            if expires_at and int(time.time()) > (expires_at - 300):
                if refresh_token:
                    logger.info("Kakao token expired for user %s, refreshing...", user_id)
                    refreshed = await self._refresh_token(user_id, refresh_token)
                    if refreshed:
                        return refreshed
                    logger.warning("Kakao token refresh failed for user %s", user_id)
                    return None
                return None

            return access_token
        except Exception:
            logger.exception("Error getting Kakao token from Supabase")
            return None

    def _sync_delete_token(self, user_id: str) -> None:
        """Synchronous token delete (runs in thread)."""
        self.db.table("kakao_tokens").delete().eq("user_id", user_id).execute()

    async def delete_token(self, user_id: str) -> bool:
        """Delete stored token for a user."""
        try:
            await asyncio.to_thread(self._sync_delete_token, user_id)
            return True
        except Exception:
            logger.exception("Error deleting Kakao token")
            return False

    async def is_connected(self, user_id: str) -> bool:
        """Check if user has connected Kakao."""
        token = await self.get_stored_token(user_id)
        return token is not None

    async def send_message_to_me(
        self, access_token: str, text: str, link_title: str | None = None, link_url: str | None = None
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
            "link": {"web_url": link_url or "https://memoir.ai", "mobile_web_url": link_url or "https://memoir.ai"},
        }

        if link_title:
            template_object["button_title"] = link_title

        async with httpx.AsyncClient() as client:
            response = await client.post(
                KAKAO_MESSAGE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"template_object": json.dumps(template_object)},
            )

            result = response.json()

            if response.status_code != 200:
                raise Exception(f"Kakao message send failed: {result}")

            return result

    async def send_memoir_notification(
        self, user_id: str, memory_title: str, memory_summary: str, memory_id: str | None = None
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
                access_token=token, text=text, link_title="Memoir에서 보기", link_url=link_url
            )
            return True
        except Exception:
            logger.exception("Failed to send Kakao message")
            return False
