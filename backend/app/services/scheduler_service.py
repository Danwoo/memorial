import logging
from datetime import UTC, datetime
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config.database import get_supabase_client
from app.repositories.chat_repository import ChatRepository
from app.repositories.diary_repository import DiaryRepository
from app.repositories.scrap_repository import ScrapRepository
from app.services.digest_service import DigestService
from app.services.nudge_service import (
    connection_discovery_job,
    evening_review_job,
    weekly_summary_job,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def _build_digest_service() -> DigestService:
    """스케줄러 컨텍스트용 DigestService 인스턴스 생성."""
    db = get_supabase_client()
    return DigestService(
        scrap_repo=ScrapRepository(db),
        diary_repo=DiaryRepository(db),
        chat_repo=ChatRepository(db),
    )


async def _get_eligible_users(current_hour: int) -> list[dict]:
    """현재 시각(KST)에 다이제스트를 받아야 할 사용자 목록 조회."""
    db = get_supabase_client()
    try:
        result = (
            db.table("kakao_bot_settings")
            .select("user_id")
            .eq("enabled", True)
            .eq("delivery_hour", current_hour)
            .execute()
        )
        return result.data or []
    except Exception:
        logger.exception("다이제스트 대상 사용자 조회 실패")
        return []


async def _record_delivery(user_id: str, status: str, error_message: str | None = None) -> None:
    """다이제스트 전송 결과 기록."""
    db = get_supabase_client()
    try:
        db.table("kakao_delivery_log").insert(
            {
                "user_id": user_id,
                "digest_date": datetime.now(UTC).strftime("%Y-%m-%d"),
                "status": status,
                "error_message": error_message,
                "delivered_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
    except Exception:
        logger.exception("다이제스트 전송 기록 실패: user_id=%s", user_id)


async def digest_delivery_job() -> None:
    """매 시간 실행: 현재 시각에 해당하는 사용자에게 다이제스트 생성 및 전송."""
    now_kst = datetime.now(UTC).astimezone()
    current_hour = now_kst.hour
    logger.info("다이제스트 배달 작업 시작: KST %02d시", current_hour)

    users = await _get_eligible_users(current_hour)
    if not users:
        logger.info("대상 사용자 없음, 작업 종료")
        return

    digest_service = _build_digest_service()

    for user_row in users:
        user_id_str = user_row["user_id"]
        try:
            user_id = UUID(user_id_str)
            digest = await digest_service.get_today_digest(user_id)

            total_items = digest["summary"]["scrap_count"] + digest["summary"]["diary_count"]
            if total_items == 0:
                logger.info("사용자 %s: 오늘 활동 없음, 건너뜀", user_id_str[:8])
                await _record_delivery(user_id_str, "skipped_empty")
                continue

            # TODO: 카카오 메시지 API로 실제 전송 (비즈니스 채널 인증 후)
            logger.info(
                "사용자 %s: 다이제스트 생성 완료 (스크랩 %d, 다이어리 %d)",
                user_id_str[:8],
                digest["summary"]["scrap_count"],
                digest["summary"]["diary_count"],
            )
            await _record_delivery(user_id_str, "generated")

        except Exception:
            logger.exception("사용자 %s 다이제스트 처리 실패", user_id_str[:8])
            await _record_delivery(user_id_str, "error", error_message="digest generation failed")


def start_scheduler() -> None:
    """스케줄러 시작: 다이제스트 + 넛지 작업 등록."""
    scheduler.add_job(
        digest_delivery_job,
        "cron",
        minute=0,
        id="digest_delivery",
        replace_existing=True,
    )
    # 저녁 회고 넛지: 매 정시 실행 (사용자별 delivery_hour에 맞춰 전송)
    scheduler.add_job(
        evening_review_job,
        "cron",
        minute=0,
        id="evening_review_nudge",
        replace_existing=True,
    )
    # 주간 요약 넛지: 매주 일요일 10시 실행
    scheduler.add_job(
        weekly_summary_job,
        "cron",
        day_of_week="sun",
        hour=10,
        minute=0,
        id="weekly_summary_nudge",
        replace_existing=True,
    )
    # 연결 발견 넛지: 매일 오전 9시 실행
    scheduler.add_job(
        connection_discovery_job,
        "cron",
        hour=9,
        minute=0,
        id="connection_discovery_nudge",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("스케줄러 시작됨 (다이제스트 + 넛지 3종)")


def stop_scheduler() -> None:
    """스케줄러 정지."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("다이제스트 스케줄러 종료됨")
