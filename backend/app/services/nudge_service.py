import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.config.database import get_supabase_client
from app.repositories.memory_repository import MemoryRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.stats_repository import StatsRepository
from app.repositories.vector_repository import VectorRepository
from app.services.push_service import send_push_notification
from app.services.stats_service import StatsService
from app.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

# 연결 발견 임계값
CONNECTION_SIMILARITY_THRESHOLD = 0.85
CONNECTION_MIN_GAP_DAYS = 3
MAX_DAILY_CONNECTION_NUDGES = 1
EVENING_REVIEW_TITLE = "오늘의 회고"
WEEKLY_SUMMARY_TITLE = "주간 요약"
CONNECTION_FOUND_TITLE = "기억 연결 발견"


def _get_repos() -> tuple[NotificationRepository, MemoryRepository, VectorRepository]:
    """스케줄러 컨텍스트용 리포지토리 인스턴스 생성."""
    db = get_supabase_client()
    return (
        NotificationRepository(db),
        MemoryRepository(db),
        VectorRepository(db),
    )


async def _get_nudge_eligible_users(
    notif_repo: NotificationRepository,
    nudge_type: str,
    current_hour: int | None = None,
) -> list[str]:
    """특정 넛지 타입이 활성화된 사용자 목록 조회."""
    db = notif_repo.db
    query = db.table("notification_settings").select("user_id").eq("nudge_type", nudge_type).eq("enabled", True)
    if current_hour is not None:
        query = query.eq("delivery_hour", current_hour)
    result = query.execute()
    return [row["user_id"] for row in (result.data or [])]


async def _send_nudge_to_user(
    notif_repo: NotificationRepository,
    user_id: str,
    nudge_type: str,
    title: str,
    body: str,
    url: str = "/",
) -> bool:
    """사용자에게 푸시 알림 전송 + 로그 기록."""
    subscriptions = notif_repo.get_push_subscriptions(UUID(user_id))
    if not subscriptions:
        logger.debug("사용자 %s: 푸시 구독 없음, 건너뜀", user_id[:8])
        return False

    sent = False
    for sub in subscriptions:
        success = send_push_notification(
            endpoint=sub["endpoint"],
            p256dh=sub["p256dh"],
            auth=sub["auth"],
            title=title,
            body=body,
            url=url,
        )
        if success:
            sent = True

    status = "sent" if sent else "failed"
    notif_repo.log_notification(
        user_id=user_id,
        nudge_type=nudge_type,
        content=f"{title}: {body}",
        status=status,
    )
    return sent


async def evening_review_job() -> None:
    """저녁 회고 넛지: 오늘 수집된 메모리 수 + 주요 토픽 → 저널 작성 유도."""
    now_kst = datetime.now(UTC).astimezone()
    current_hour = now_kst.hour
    logger.info("저녁 회고 넛지 시작: KST %02d시", current_hour)

    notif_repo, memory_repo, _ = _get_repos()
    users = await _get_nudge_eligible_users(notif_repo, "evening_review", current_hour)

    if not users:
        logger.info("저녁 회고 대상 사용자 없음")
        return

    today = datetime.now(UTC).date()
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)
    today_end = datetime.combine(today, datetime.max.time(), tzinfo=UTC)

    for user_id in users:
        try:
            all_memories = await memory_repo.get_all(user_id=UUID(user_id))
            today_memories = []
            for mem in all_memories:
                created_str = mem.get("created_at", "")
                if created_str:
                    try:
                        created_at = parse_iso_datetime(created_str)
                        if today_start <= created_at <= today_end:
                            today_memories.append(mem)
                    except (ValueError, TypeError):
                        continue

            count = len(today_memories)
            if count == 0:
                logger.info("사용자 %s: 오늘 활동 없음, 건너뜀", user_id[:8])
                continue

            # 주요 토픽 추출
            tag_counts: dict[str, int] = {}
            for mem in today_memories:
                for tag in mem.get("tags") or []:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:3]

            topics_str = ", ".join(top_tags) if top_tags else "다양한 주제"
            body = f"오늘 {count}개의 새 기억이 쌓였습니다. {topics_str} 주제로 저널을 써볼까요?"

            await _send_nudge_to_user(
                notif_repo,
                user_id,
                "evening_review",
                EVENING_REVIEW_TITLE,
                body,
                url="/journal",
            )
            logger.info("사용자 %s: 저녁 회고 넛지 전송 (메모리 %d개)", user_id[:8], count)

        except Exception:
            logger.exception("사용자 %s 저녁 회고 넛지 실패", user_id[:8])


async def weekly_summary_job() -> None:
    """주간 요약 넛지: 이번 주 통계 + 가장 많이 다룬 주제 + 스트릭 현황."""
    logger.info("주간 요약 넛지 시작")

    notif_repo, _, _ = _get_repos()
    users = await _get_nudge_eligible_users(notif_repo, "weekly_summary")

    if not users:
        logger.info("주간 요약 대상 사용자 없음")
        return

    db = get_supabase_client()
    stats_service = StatsService(StatsRepository(db))

    for user_id in users:
        try:
            overview = await stats_service.get_overview(UUID(user_id))
            streak = await stats_service.get_streak(UUID(user_id))

            weekly_count = overview.overview.total_this_week
            current_streak = streak.current_streak
            top_tags = overview.top_tags

            if weekly_count == 0:
                logger.info("사용자 %s: 이번 주 활동 없음, 건너뜀", user_id[:8])
                continue

            topics = [t.tag for t in top_tags[:3]] if top_tags else []
            topics_str = ", ".join(topics) if topics else "다양한 주제"

            parts = [f"이번 주 {weekly_count}개의 기억을 저장했습니다."]
            if current_streak > 0:
                parts.append(f"연속 {current_streak}일째 기록 중!")
            parts.append(f"주요 관심사: {topics_str}")

            body = " ".join(parts)

            await _send_nudge_to_user(
                notif_repo,
                user_id,
                "weekly_summary",
                WEEKLY_SUMMARY_TITLE,
                body,
                url="/dashboard",
            )
            logger.info("사용자 %s: 주간 요약 넛지 전송", user_id[:8])

        except Exception:
            logger.exception("사용자 %s 주간 요약 넛지 실패", user_id[:8])


async def connection_discovery_job() -> None:
    """연결 발견 넛지: 최근 메모리와 기존 메모리 사이 유사도 검사."""
    logger.info("연결 발견 넛지 시작")

    notif_repo, memory_repo, vector_repo = _get_repos()
    users = await _get_nudge_eligible_users(notif_repo, "connection_found")

    if not users:
        logger.info("연결 발견 대상 사용자 없음")
        return

    yesterday = datetime.now(UTC) - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday.date(), datetime.min.time(), tzinfo=UTC)
    yesterday_end = datetime.combine(yesterday.date(), datetime.max.time(), tzinfo=UTC)

    for user_id in users:
        try:
            all_memories = await memory_repo.get_all(user_id=UUID(user_id))

            # 어제 저장된 메모리 추출
            recent_memories = []
            older_memories = []
            for mem in all_memories:
                created_str = mem.get("created_at", "")
                if not created_str:
                    continue
                try:
                    created_at = parse_iso_datetime(created_str)
                except (ValueError, TypeError):
                    continue

                if yesterday_start <= created_at <= yesterday_end:
                    recent_memories.append(mem)
                elif created_at < yesterday_start - timedelta(days=CONNECTION_MIN_GAP_DAYS):
                    older_memories.append(mem)

            if not recent_memories:
                continue

            nudges_sent = 0
            for mem in recent_memories:
                if nudges_sent >= MAX_DAILY_CONNECTION_NUDGES:
                    break

                content = mem.get("content") or mem.get("summary") or mem.get("title", "")
                if not content:
                    continue

                # 벡터 유사도 검색
                results = await vector_repo.similarity_search(
                    query=content,
                    limit=3,
                    threshold=CONNECTION_SIMILARITY_THRESHOLD,
                    filters={"user_id": user_id},
                )

                for result in results:
                    if str(result.get("id")) == str(mem.get("id")):
                        continue

                    # 시간 간격 확인
                    result_date_str = result.get("created_at", "")
                    if result_date_str:
                        try:
                            result_date = parse_iso_datetime(result_date_str)
                            gap = abs((parse_iso_datetime(mem.get("created_at", "")) - result_date).days)
                            if gap < CONNECTION_MIN_GAP_DAYS:
                                continue
                        except (ValueError, TypeError):
                            pass

                    new_title = mem.get("title", "최근 메모리")
                    old_title = result.get("title", "과거 메모리")
                    body = f"'{new_title}'가 '{old_title}'와 연결됩니다. 어떤 관계가 있을까요?"

                    await _send_nudge_to_user(
                        notif_repo,
                        user_id,
                        "connection_found",
                        CONNECTION_FOUND_TITLE,
                        body,
                        url="/graph",
                    )
                    nudges_sent += 1
                    logger.info("사용자 %s: 연결 발견 넛지 전송", user_id[:8])
                    break  # 메모리당 1개 연결만

        except Exception:
            logger.exception("사용자 %s 연결 발견 넛지 실패", user_id[:8])
