import logging
import time
from collections import Counter
from uuid import UUID

from app.config.database import get_supabase_client

logger = logging.getLogger(__name__)

PROFILE_TTL_SECONDS = 24 * 60 * 60  # 24시간
TOP_INTERESTS_LIMIT = 5
RECENT_DAYS = 14

_profile_cache: dict[str, tuple[float, dict]] = {}
MAX_PROFILE_CACHE_SIZE = 256


async def get_user_profile(user_id: UUID | str) -> dict | None:
    """사용자 메모리 태그 빈도 + 최근 저널 키워드로 관심사 프로필 생성.

    24시간 TTL 캐시를 사용하여 반복 호출 시 DB 조회를 방지한다.
    """
    uid = str(user_id)

    cached = _profile_cache.get(uid)
    if cached:
        ts, profile = cached
        if time.time() - ts < PROFILE_TTL_SECONDS:
            return profile

    try:
        profile = await _build_profile(uid)
        if len(_profile_cache) >= MAX_PROFILE_CACHE_SIZE:
            oldest_key = min(_profile_cache, key=lambda k: _profile_cache[k][0])
            del _profile_cache[oldest_key]
        _profile_cache[uid] = (time.time(), profile)
        return profile
    except Exception:
        logger.exception("사용자 프로필 생성 실패: user_id=%s", uid)
        return None


async def _build_profile(user_id: str) -> dict:
    """DB에서 태그 빈도 + 최근 기억 주제를 조합하여 프로필 딕셔너리 생성."""
    import asyncio

    db = get_supabase_client()

    tags_result, recent_result, stats_result = await asyncio.gather(
        asyncio.to_thread(
            lambda: db.table("memories").select("tags").eq("user_id", user_id).not_.is_("tags", "null").execute()
        ),
        asyncio.to_thread(
            lambda: db.table("memories")
            .select("title, tags, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        ),
        asyncio.to_thread(lambda: db.table("memories").select("id", count="exact").eq("user_id", user_id).execute()),
    )

    # 태그 빈도 집계
    tag_counter: Counter = Counter()
    for row in tags_result.data or []:
        tags = row.get("tags")
        if tags:
            for tag in tags:
                if isinstance(tag, str):
                    tag_counter[tag] += 1

    top_interests = [tag for tag, _ in tag_counter.most_common(TOP_INTERESTS_LIMIT)]

    # 최근 2주 기억에서 주제 추출
    recent_topics: list[str] = []
    seen: set[str] = set()
    for row in recent_result.data or []:
        tags = row.get("tags") or []
        for tag in tags:
            if isinstance(tag, str) and tag not in seen and tag not in top_interests:
                seen.add(tag)
                recent_topics.append(tag)
                if len(recent_topics) >= 3:
                    break
        if len(recent_topics) >= 3:
            break

    memory_count = stats_result.count if stats_result.count else 0

    return {
        "top_interests": top_interests,
        "recent_topics": recent_topics,
        "memory_count": memory_count,
    }


def invalidate_profile_cache(user_id: str | UUID) -> None:
    """특정 사용자의 프로필 캐시를 강제 무효화."""
    _profile_cache.pop(str(user_id), None)
