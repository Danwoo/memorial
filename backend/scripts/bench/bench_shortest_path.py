"""KuzuDB shortest path: portable (variable-length + sort) vs native (`*SHORTEST`).

이 벤치마크의 발견:
- KuzuDB 0.11의 Cypher는 Neo4j 표준 list-comprehension `[n IN nodes(p) | n.name]`을 미지원
- 대신 `list_transform(nodes(p), x -> x.name)` 사용
- `*SHORTEST` 키워드는 0.11에서 정상 동작 — portable 우회 불필요

실행:
    .venv/bin/python -m scripts.bench.bench_shortest_path
"""

from __future__ import annotations

import statistics
import sys
import tempfile
import time
from pathlib import Path

import kuzu

NODE_COUNT = 200
EDGE_DENSITY = 4
MAX_HOPS = 3
REPEAT = 5
QUERIES_PER_REPEAT = 20


def setup_graph(path: str, n: int) -> kuzu.Database:
    db = kuzu.Database(path, buffer_pool_size=128 * 1024 * 1024)
    conn = kuzu.Connection(db)
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Entity(name STRING, type STRING, PRIMARY KEY(name))")
    conn.execute("CREATE NODE TABLE IF NOT EXISTS Memory(id STRING, user_id STRING, PRIMARY KEY(id))")
    conn.execute("CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Memory TO Entity)")
    conn.execute("CREATE REL TABLE IF NOT EXISTS ENTITY_REL(FROM Entity TO Entity, rel_type STRING)")

    entities = [{"name": f"E{i}", "type": "Concept"} for i in range(n)]
    conn.execute("UNWIND $es AS e MERGE (n:Entity {name: e.name}) SET n.type = e.type", {"es": entities})
    conn.execute("MERGE (m:Memory {id: 'bench'}) SET m.user_id = 'bench-user'")
    conn.execute(
        """UNWIND $names AS n
        MATCH (m:Memory {id: 'bench'}), (e:Entity {name: n})
        CREATE (m)-[:MENTIONS]->(e)""",
        {"names": [e["name"] for e in entities]},
    )

    rels = []
    for i in range(n):
        for k in range(1, EDGE_DENSITY + 1):
            j = (i + k) % n
            if i != j:
                rels.append({"source": f"E{i}", "target": f"E{j}", "rel_type": "RELATED_TO"})
    conn.execute(
        """UNWIND $rs AS r
        MATCH (a:Entity {name: r.source}), (b:Entity {name: r.target})
        CREATE (a)-[:ENTITY_REL {rel_type: r.rel_type}]->(b)""",
        {"rs": rels},
    )
    return db


def measure_portable(db: kuzu.Database, source: str, target: str) -> float:
    """variable-length + length sort 방식 (KuzuDB 미지원 키워드 회피 시 사용)."""
    conn = kuzu.Connection(db)
    query = f"""
    MATCH (a:Entity {{name: $source}}), (b:Entity {{name: $target}})
    WHERE EXISTS {{ MATCH (ma:Memory {{user_id: $uid}})-[:MENTIONS]->(a) }}
      AND EXISTS {{ MATCH (mb:Memory {{user_id: $uid}})-[:MENTIONS]->(b) }}
    MATCH p = (a)-[r:ENTITY_REL*1..{MAX_HOPS}]-(b)
    RETURN list_transform(nodes(p), x -> x.name) AS names, length(p) AS hops
    ORDER BY hops ASC LIMIT 1
    """
    start = time.perf_counter()
    result = conn.execute(query, {"source": source, "target": target, "uid": "bench-user"})
    while result.has_next():
        result.get_next()
    return time.perf_counter() - start


def measure_native(db: kuzu.Database, source: str, target: str) -> float:
    """KuzuDB `* SHORTEST` — 운영 코드가 채택한 방식."""
    conn = kuzu.Connection(db)
    query = f"""
    MATCH (a:Entity {{name: $source}}), (b:Entity {{name: $target}})
    WHERE EXISTS {{ MATCH (ma:Memory {{user_id: $uid}})-[:MENTIONS]->(a) }}
      AND EXISTS {{ MATCH (mb:Memory {{user_id: $uid}})-[:MENTIONS]->(b) }}
    MATCH p = (a)-[r:ENTITY_REL* SHORTEST 1..{MAX_HOPS}]-(b)
    RETURN list_transform(nodes(p), x -> x.name) AS names, length(p) AS hops
    LIMIT 1
    """
    start = time.perf_counter()
    result = conn.execute(query, {"source": source, "target": target, "uid": "bench-user"})
    while result.has_next():
        result.get_next()
    return time.perf_counter() - start


def fmt_ms(s: float) -> str:
    return f"{s * 1000:.2f}ms"


def main() -> None:
    print("=" * 72)
    print(f"Shortest Path: portable vs native (노드={NODE_COUNT}, 평균 out-edge={EDGE_DENSITY}, max_hops={MAX_HOPS})")
    print("=" * 72)

    with tempfile.TemporaryDirectory() as td:
        db = setup_graph(str(Path(td) / "bench.kuzu"), NODE_COUNT)

        portable_times: list[float] = []
        native_times: list[float] = []
        for _ in range(REPEAT):
            for q in range(QUERIES_PER_REPEAT):
                src = f"E{q * 3 % NODE_COUNT}"
                dst = f"E{(q * 3 + 7) % NODE_COUNT}"
                portable_times.append(measure_portable(db, src, dst))
                native_times.append(measure_native(db, src, dst))

        p_med = statistics.median(portable_times)
        n_med = statistics.median(native_times)
        p_p95 = statistics.quantiles(portable_times, n=20)[18]
        n_p95 = statistics.quantiles(native_times, n=20)[18]
        print(f"{'metric':>10} | {'portable':>12} | {'native':>12}")
        print(f"{'median':>10} | {fmt_ms(p_med):>12} | {fmt_ms(n_med):>12}")
        print(f"{'p95':>10} | {fmt_ms(p_p95):>12} | {fmt_ms(n_p95):>12}")
        print(f"\nnative speedup (median): {p_med / n_med:.2f}x")
        print("\n해석: native는 BFS로 첫 발견 즉시 반환 — portable은 모든 path 생성 후 정렬.")
        print("운영 코드는 native 채택 (mindmap/_path.py).")


if __name__ == "__main__":
    sys.exit(main() or 0)
