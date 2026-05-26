"""KuzuDB UNWIND 배치 vs for-loop 1-by-1 성능 측정.

목적: commit log에 적은 "UNWIND가 N배 빠르다"는 주장을 수치로 검증한다.

실행:
    .venv/bin/python -m scripts.bench.bench_graph_batch

결과는 stdout에 출력. 변수:
- entity_count: 단일 batch에 적재할 엔티티 수
- 반복 횟수: 통계적 안정성 확보용
"""

from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path

import kuzu

# 측정 시나리오
ENTITY_COUNTS = [10, 50, 200, 1000]
REPEAT = 5  # 통계 안정성


def setup_db(path: str) -> kuzu.Database:
    db = kuzu.Database(path, buffer_pool_size=64 * 1024 * 1024)
    conn = kuzu.Connection(db)
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Entity(name STRING, type STRING, PRIMARY KEY(name))")
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Memory(id STRING, user_id STRING, PRIMARY KEY(id))")
    conn.execute("CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Memory TO Entity)")
    return db


def gen_entities(n: int, prefix: str) -> list[dict]:
    return [{"name": f"{prefix}_Entity_{i}", "type": "Concept"} for i in range(n)]


def measure_for_loop(db: kuzu.Database, entities: list[dict], source_id: str) -> float:
    """기존 패턴 — 엔티티마다 conn.execute() 호출."""
    conn = kuzu.Connection(db)
    start = time.perf_counter()

    for e in entities:
        conn.execute(
            "MERGE (n:Entity {name: $name}) SET n.type = $type",
            {"name": e["name"], "type": e["type"]},
        )
    conn.execute(
        "MERGE (m:Memory {id: $id}) SET m.user_id = $user_id",
        {"id": source_id, "user_id": "bench-user"},
    )
    for e in entities:
        conn.execute(
            """
            MATCH (m:Memory {id: $id}), (e:Entity {name: $name})
            WHERE NOT EXISTS { MATCH (m)-[:MENTIONS]->(e) }
            CREATE (m)-[:MENTIONS]->(e)
            """,
            {"id": source_id, "name": e["name"]},
        )

    return time.perf_counter() - start


def measure_unwind_batch(db: kuzu.Database, entities: list[dict], source_id: str) -> float:
    """현재 패턴 — UNWIND 단일 쿼리."""
    conn = kuzu.Connection(db)
    start = time.perf_counter()

    conn.execute(
        """
        UNWIND $entities AS e
        MERGE (n:Entity {name: e.name}) SET n.type = e.type
        """,
        {"entities": entities},
    )
    conn.execute(
        "MERGE (m:Memory {id: $id}) SET m.user_id = $user_id",
        {"id": source_id, "user_id": "bench-user"},
    )
    conn.execute(
        """
        UNWIND $names AS n
        MATCH (m:Memory {id: $id}), (e:Entity {name: n})
        WHERE NOT EXISTS { MATCH (m)-[:MENTIONS]->(e) }
        CREATE (m)-[:MENTIONS]->(e)
        """,
        {"id": source_id, "names": [e["name"] for e in entities]},
    )

    return time.perf_counter() - start


def fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000:.2f}ms"


def main() -> None:
    print("=" * 72)
    print("KuzuDB UNWIND 배치 vs for-loop 1-by-1 성능 측정")
    print(f"각 시나리오 {REPEAT}회 반복, median 보고")
    print("=" * 72)
    print(f"{'엔티티':>8} | {'for-loop':>14} | {'UNWIND':>14} | {'speedup':>10}")
    print("-" * 72)

    for n in ENTITY_COUNTS:
        loop_times: list[float] = []
        unwind_times: list[float] = []

        for rep in range(REPEAT):
            with tempfile.TemporaryDirectory() as td:
                # for-loop 측정
                db = setup_db(str(Path(td) / "loop.kuzu"))
                entities = gen_entities(n, f"loop_{rep}")
                loop_times.append(measure_for_loop(db, entities, f"src_loop_{rep}"))
                del db  # close

                # UNWIND 측정 (별도 DB)
                db = setup_db(str(Path(td) / "unwind.kuzu"))
                entities = gen_entities(n, f"unwind_{rep}")
                unwind_times.append(measure_unwind_batch(db, entities, f"src_unwind_{rep}"))
                del db

        loop_med = statistics.median(loop_times)
        unwind_med = statistics.median(unwind_times)
        speedup = loop_med / unwind_med if unwind_med > 0 else float("inf")
        print(
            f"{n:>8} | {fmt_ms(loop_med):>14} | {fmt_ms(unwind_med):>14} | "
            f"{speedup:>9.2f}x"
        )

    print("-" * 72)
    print("해석: UNWIND는 plan compile 1회 + 단일 round-trip. for-loop는 N회 plan + N round-trip.")
    print("실제 DB가 임베디드라 round-trip 비용 미미 — 차이의 주 원인은 plan compile.")


if __name__ == "__main__":
    sys.exit(main() or 0)
