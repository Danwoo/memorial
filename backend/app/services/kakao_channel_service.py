import logging
import re
import secrets
from datetime import UTC, datetime, timedelta

from supabase import Client

from app.schemas.integration_schema import KakaoSkillResponse
from app.services.ingest_service import process_note_content, process_web_content
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)
LINK_CODE_PATTERN = re.compile(r"^#연결\s+(MEMOIR-[A-Z0-9]{6})$")
DISCONNECT_COMMAND = "#해제"
HELP_COMMAND = "#도움말"

HELP_TEXT = (
    "Memoir 사용법\n\n"
    "- URL 전송: 웹 페이지를 Memoir에 저장합니다\n"
    "- 텍스트 전송: 노트로 저장합니다\n"
    "- #연결 MEMOIR-XXXXXX: 계정을 연결합니다\n"
    "- #해제: 채널 연결을 해제합니다\n"
    "- #도움말: 이 안내를 표시합니다"
)

# 연결 코드 유효 시간
LINK_CODE_EXPIRY = timedelta(minutes=30)
# 카카오톡 메시지 미리보기 최대 길이
KAKAO_PREVIEW_MAX_LENGTH = 20
# 카카오톡 제목 미리보기 최대 길이
KAKAO_TITLE_MAX_LENGTH = 30


class KakaoChannelService:
    """카카오 OpenBuilder 웹훅 처리, 채널 계정 연동, 스킬 응답 생성."""

    def __init__(self, db: Client, memory_service: MemoryService) -> None:
        self.db = db
        self.memory_service = memory_service

    # --- 공개 API ---

    def lookup_user_id(self, bot_user_key: str) -> str | None:
        """bot_user_key로 매핑된 user_id 조회."""
        result = (
            self.db.table("kakao_channel_mappings")
            .select("user_id")
            .eq("bot_user_key", bot_user_key)
            .eq("channel_status", "active")
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["user_id"]
        return None

    async def process_webhook(
        self,
        utterance: str,
        bot_user_key: str,
        plusfriend_user_key: str | None = None,
    ) -> KakaoSkillResponse:
        """웹훅 메인 라우팅: 콘텐츠 타입 판별 후 적절한 처리 수행."""
        utterance = utterance.strip()

        if utterance == HELP_COMMAND:
            return KakaoSkillResponse.simple_text(HELP_TEXT)

        link_match = LINK_CODE_PATTERN.match(utterance)
        if link_match:
            return await self._handle_link_code(link_match.group(1), bot_user_key, plusfriend_user_key)

        user_id = self.lookup_user_id(bot_user_key)
        if not user_id:
            return self._build_link_required_response()

        if utterance == DISCONNECT_COMMAND:
            return self._handle_disconnect(bot_user_key)

        if URL_PATTERN.match(utterance):
            return await self._save_url_memory(utterance, user_id)

        return await self._save_text_memory(utterance, user_id)

    def generate_link_code(self, user_id: str) -> dict:
        """6자리 연결 코드 생성 후 pending_channel_links에 저장."""
        code = f"MEMOIR-{secrets.token_hex(3).upper()}"

        self.db.table("pending_channel_links").insert(
            {
                "user_id": user_id,
                "link_code": code,
            }
        ).execute()

        # DB에서 expires_at 조회 (DB 기본값 사용), 실패 시 로컬 계산으로 폴백
        result = self.db.table("pending_channel_links").select("expires_at").eq("link_code", code).limit(1).execute()
        if result.data:
            db_expires_at = result.data[0]["expires_at"]
        else:
            db_expires_at = (datetime.now(UTC) + LINK_CODE_EXPIRY).isoformat()

        return {
            "code": code,
            "expires_at": db_expires_at,
            "instructions": f"카카오톡에서 Memoir 채널에 다음 메시지를 보내주세요:\n#연결 {code}",
        }

    def get_channel_status(self, user_id: str) -> dict:
        """사용자의 활성 채널 매핑 상태 조회."""
        result = (
            self.db.table("kakao_channel_mappings")
            .select("bot_user_key, linked_at")
            .eq("user_id", user_id)
            .eq("channel_status", "active")
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            return {
                "connected": True,
                "bot_user_key": row["bot_user_key"],
                "linked_at": row["linked_at"],
            }
        return {"connected": False, "bot_user_key": None, "linked_at": None}

    def disconnect_channel(self, user_id: str) -> bool:
        """채널 매핑 소프트 삭제 (status를 inactive로 변경)."""
        result = (
            self.db.table("kakao_channel_mappings")
            .update({"channel_status": "inactive", "updated_at": "now()"})
            .eq("user_id", user_id)
            .eq("channel_status", "active")
            .execute()
        )
        return bool(result.data)

    # --- 내부 메서드 ---

    async def _handle_link_code(
        self,
        code: str,
        bot_user_key: str,
        plusfriend_user_key: str | None,
    ) -> KakaoSkillResponse:
        """연결 코드 검증 후 채널 매핑 생성."""
        result = (
            self.db.table("pending_channel_links")
            .select("user_id, expires_at, used")
            .eq("link_code", code)
            .limit(1)
            .execute()
        )
        if not result.data:
            return KakaoSkillResponse.simple_text("유효하지 않은 연결 코드입니다. Settings에서 새 코드를 생성해주세요.")

        link = result.data[0]
        if link["used"]:
            return KakaoSkillResponse.simple_text("이미 사용된 연결 코드입니다.")

        expires_at = datetime.fromisoformat(link["expires_at"].replace("Z", "+00:00"))
        if datetime.now(UTC) > expires_at:
            return KakaoSkillResponse.simple_text("만료된 연결 코드입니다. Settings에서 새 코드를 생성해주세요.")

        user_id = link["user_id"]

        self.db.table("pending_channel_links").update({"used": True}).eq("link_code", code).execute()

        self.db.table("kakao_channel_mappings").upsert(
            {
                "user_id": user_id,
                "bot_user_key": bot_user_key,
                "plusfriend_user_key": plusfriend_user_key,
                "channel_status": "active",
                "updated_at": "now()",
            },
            on_conflict="bot_user_key",
        ).execute()

        return KakaoSkillResponse.simple_text(
            "계정 연결이 완료되었습니다! 이제 URL이나 텍스트를 보내면 Memoir에 자동 저장됩니다."
        )

    def _handle_disconnect(self, bot_user_key: str) -> KakaoSkillResponse:
        """채팅 명령으로 채널 연결 해제."""
        self.db.table("kakao_channel_mappings").update({"channel_status": "inactive", "updated_at": "now()"}).eq(
            "bot_user_key", bot_user_key
        ).execute()

        return KakaoSkillResponse.simple_text(
            "채널 연결이 해제되었습니다. 다시 연결하려면 Settings에서 새 연결 코드를 생성해주세요."
        )

    async def _save_url_memory(self, url: str, user_id: str) -> KakaoSkillResponse:
        """URL 크롤링 후 Memory로 저장."""
        try:
            processed = await process_web_content(url)
            await self.memory_service.create_memory(
                user_id=user_id,
                title=processed["title"],
                content=processed["content"],
                source_type="KAKAO",
                source_url=processed.get("source_url"),
            )
            title = processed["title"][:KAKAO_TITLE_MAX_LENGTH]
            return KakaoSkillResponse.simple_text(f"저장 완료! '{title}'이(가) Memoir에 추가되었습니다.")
        except Exception:
            logger.exception("Failed to save URL memory from Kakao: %s", url)
            return KakaoSkillResponse.simple_text("URL 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")

    async def _save_text_memory(self, text: str, user_id: str) -> KakaoSkillResponse:
        """일반 텍스트를 노트 Memory로 저장."""
        try:
            processed = await process_note_content(text)
            await self.memory_service.create_memory(
                user_id=user_id,
                title=processed["title"],
                content=processed["content"],
                source_type="KAKAO",
                source_url=None,
            )
            preview = text[:KAKAO_PREVIEW_MAX_LENGTH] + "..." if len(text) > KAKAO_PREVIEW_MAX_LENGTH else text
            return KakaoSkillResponse.simple_text(f"메모 저장 완료! '{preview}'이(가) Memoir에 추가되었습니다.")
        except Exception:
            logger.exception("Failed to save text memory from Kakao")
            return KakaoSkillResponse.simple_text("메모 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")

    @staticmethod
    def _build_link_required_response() -> KakaoSkillResponse:
        return KakaoSkillResponse.simple_text(
            "Memoir 계정과 연결되지 않았습니다.\n\n"
            "1. memoir.dev 에서 Settings 페이지로 이동\n"
            "2. '카카오톡 채널 연결' 에서 연결 코드 생성\n"
            "3. 이 채팅에서 '#연결 MEMOIR-XXXXXX' 입력\n\n"
            "도움말: #도움말"
        )
