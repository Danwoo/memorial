"""AgentServiceContainer 생성 비용 측정 (ADR-007 검증).

매 호출마다 새 container를 만드는 정책이 정당한지 수치로 확인.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from unittest.mock import MagicMock

# Supabase 의존 회피 — Mock으로 환경변수 셋업
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("KUZU_DB_PATH", "")


def main() -> None:
    from app.agents import container as container_module

    # Supabase 클라이언트 mock — DB 호출 회피
    container_module.get_supabase_client = lambda: MagicMock()

    print("=" * 60)
    print("AgentServiceContainer 생성 비용 (1000회 반복)")
    print("=" * 60)

    times: list[float] = []
    for _ in range(1000):
        start = time.perf_counter()
        c = container_module.get_agent_container()
        times.append(time.perf_counter() - start)
        del c

    times.sort()
    med = statistics.median(times)
    p95 = times[int(len(times) * 0.95)]
    p99 = times[int(len(times) * 0.99)]
    print(f"median:  {med * 1000:.3f}ms")
    print(f"p95:     {p95 * 1000:.3f}ms")
    print(f"p99:     {p99 * 1000:.3f}ms")
    print(f"total (1000회): {sum(times) * 1000:.1f}ms")
    print("\n해석:")
    print("- 컨테이너 생성 비용이 1요청 응답 시간(수백 ms~수 초)의 0.1% 미만이면 per-request OK")
    print("- 초과 시 lru_cache singleton 또는 lazy property 패턴 검토")


if __name__ == "__main__":
    sys.exit(main() or 0)
