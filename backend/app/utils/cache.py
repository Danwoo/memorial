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
        """전체 캐시 초기화."""
        self._store.clear()


# 전역 캐시 인스턴스 (서비스 간 공유)
stats_cache = TTLCache(ttl_seconds=300)  # 통계: 5분
briefing_cache = TTLCache(ttl_seconds=300)  # 브리핑: 5분
tags_cache = TTLCache(ttl_seconds=600)  # 태그 목록: 10분
graph_cache = TTLCache(ttl_seconds=300)  # 그래프: 5분
