import json
import logging
from collections import OrderedDict
from time import monotonic
from typing import Any

logger = logging.getLogger(__name__)


class TTLCache:
    """사용자별 키 격리를 지원하는 단순 TTL 인메모리 캐시."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 256):
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        """캐시에서 값 조회. 만료 시 None 반환."""
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """캐시에 값 저장."""
        self._store[key] = (monotonic() + self._ttl, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """특정 키 무효화."""
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """접두사로 시작하는 모든 키 무효화."""
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in keys_to_delete:
            self._store.pop(k, None)

    def clear(self) -> None:
        """전체 캐시 초기화. RedisCache.clear()와 달리 인메모리이므로 전체 삭제가 안전하다."""
        self._store.clear()


class RedisCache:
    """Upstash Redis REST API 기반 분산 TTL 캐시.

    TTLCache와 동일한 인터페이스(get/set/invalidate/invalidate_prefix/clear)를 제공.
    값은 JSON 직렬화하여 저장하며, Upstash SDK가 자동 처리.

    주의 — 동기 클라이언트 한계:
        upstash_redis.Redis는 동기 HTTP 클라이언트(httpx sync)를 사용한다.
        async 핸들러에서 호출 시 이벤트 루프를 차단할 수 있다.
        현재 소규모 트래픽(Render Free 단일 워커) 환경에서는 허용 범위로 판단하여 유지한다.
        트래픽 증가 시 AsyncRedis(upstash_redis.asyncio.Redis)로 전환 필요.
    """

    def __init__(self, url: str, token: str, ttl_seconds: int = 300):
        from upstash_redis import Redis

        self._redis = Redis(url=url, token=token)
        self._ttl = ttl_seconds

    def get(self, key: str) -> Any | None:
        """Redis에서 값 조회. 만료되었거나 없으면 None 반환."""
        try:
            value = self._redis.get(key)
            if value is None:
                return None
            # upstash-redis SDK가 JSON 문자열을 반환할 수 있으므로 파싱 시도
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    return value
            return value
        except Exception:
            logger.warning("RedisCache.get 실패: key=%s", key, exc_info=True)
            return None

    def set(self, key: str, value: Any) -> None:
        """Redis에 값 저장 (TTL 적용)."""
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            self._redis.set(key, serialized, ex=self._ttl)
        except Exception:
            logger.warning("RedisCache.set 실패: key=%s", key, exc_info=True)

    def invalidate(self, key: str) -> None:
        """특정 키 무효화."""
        try:
            self._redis.delete(key)
        except Exception:
            logger.warning("RedisCache.invalidate 실패: key=%s", key, exc_info=True)

    def invalidate_prefix(self, prefix: str) -> None:
        """접두사로 시작하는 모든 키 무효화 (SCAN 사용)."""
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=f"{prefix}*", count=100)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            logger.warning("RedisCache.invalidate_prefix 실패: prefix=%s", prefix, exc_info=True)

    def clear(self) -> None:
        """[비활성화] 공유 Redis에서 FLUSHDB는 모든 사용자의 캐시를 삭제하므로 안전하지 않다.

        이 메서드는 의도적으로 아무 동작도 하지 않는다.
        사용자별 캐시 무효화가 필요하면 invalidate_prefix(f"<prefix>:{user_id}") 를 사용할 것.
        """
        logger.warning(
            "RedisCache.clear() 호출됨 — 공유 Redis 보호를 위해 FLUSHDB를 실행하지 않음. "
            "사용자 범위 무효화에는 invalidate_prefix()를 사용하세요."
        )


def make_cache(ttl_seconds: int = 300, max_size: int = 256) -> TTLCache | RedisCache:
    """환경변수에 따라 RedisCache 또는 TTLCache 인스턴스를 반환하는 팩토리.

    UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN 모두 설정된 경우 RedisCache 반환.
    그 외에는 TTLCache 반환 (로컬 개발 폴백 및 테스트 환경).
    """
    try:
        from app.config.settings import get_settings

        settings = get_settings()
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            logger.info("RedisCache 사용 (Upstash Redis): ttl=%ds", ttl_seconds)
            return RedisCache(
                url=settings.UPSTASH_REDIS_REST_URL,
                token=settings.UPSTASH_REDIS_REST_TOKEN,
                ttl_seconds=ttl_seconds,
            )
    except Exception:
        logger.debug("설정 로드 실패 — TTLCache 폴백 (테스트 환경 등): ttl=%ds", ttl_seconds)
    logger.debug("TTLCache 사용 (인메모리 폴백): ttl=%ds", ttl_seconds)
    return TTLCache(ttl_seconds=ttl_seconds, max_size=max_size)


# 전역 캐시 인스턴스 (서비스 간 공유)
stats_cache = make_cache(ttl_seconds=300)  # 통계: 5분
tags_cache = make_cache(ttl_seconds=600)  # 태그 목록: 10분
graph_cache = make_cache(ttl_seconds=300)  # 그래프: 5분
insights_cache = make_cache(ttl_seconds=600)  # 인사이트: 10분
report_cache = make_cache(ttl_seconds=3600)  # 리포트: 1시간
community_cache = make_cache(ttl_seconds=3600)  # 커뮤니티 요약: 1시간
