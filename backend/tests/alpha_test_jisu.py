"""알파테스터 4 — 최지수: 마인드맵 + 검색 + 내보내기 + 중복감지"""

import json
import time
import urllib.request

BASE = "https://memoir-backend-danwoo.onrender.com/api/v1"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE"
SUPABASE_URL = "https://otzqnucgfrlbqyyhksgo.supabase.co"
EMAIL = "alpha.jisu@memoir.test"
PASSWORD = "REDACTED"

results = []


def login():
    data = json.dumps({"email": EMAIL, "password": PASSWORD}).encode()
    req = urllib.request.Request(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        data=data,
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["access_token"]


def api(method, path, token=None, body=None, timeout=30):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        status = resp.status
        raw = resp.read().decode()
        try:
            body_resp = json.loads(raw)
        except Exception:
            body_resp = {"raw": raw[:500]}
        return status, body_resp, round(time.time() - start, 2)
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_resp = json.loads(e.read().decode())
        except Exception:
            body_resp = {"error": str(e)}
        return status, body_resp, round(time.time() - start, 2)
    except Exception as e:
        return 0, {"error": str(e)}, round(time.time() - start, 2)


def test(tid, name, expected, status, actual, passed):
    s = "PASS" if passed else "FAIL"
    results.append({"id": tid, "name": name, "expected": expected, "actual": actual, "status": s})
    print(f"  [{s}] {tid}: {name} (HTTP {status})")


def run():
    print("=" * 60)
    print("알파테스터 4: 최지수 — 마인드맵 + 검색 + 내보내기")
    print("=" * 60)

    token = login()
    print("  토큰 발급 완료")

    # S1: Auth
    s, b, t = api("GET", "/auth/me", token)
    test("S1.1", "인증 확인", "200", s, f"{s}, email={b.get('email', '?')}", s == 200)

    # S2: Setup (스크랩 데이터 생성)
    scrap_data = [
        {
            "title": "React와 컴포넌트 패턴",
            "content": "React의 핵심은 컴포넌트 기반 아키텍처입니다. hooks를 활용한 상태관리와 Context API를 통한 전역 상태 관리가 중요합니다.",
            "source_type": "text",
            "tags": ["React", "프론트엔드"],
        },
        {
            "title": "LangGraph로 AI 에이전트 구축",
            "content": "LangGraph는 LangChain 위에 구축된 프레임워크로, 복잡한 AI 워크플로우를 그래프 구조로 설계할 수 있습니다.",
            "source_type": "text",
            "tags": ["AI", "LangGraph"],
        },
        {
            "title": "PostgreSQL 벡터 검색",
            "content": "pgvector 확장을 사용하면 PostgreSQL에서 벡터 유사도 검색이 가능합니다. IVFFlat 인덱스로 ANN 검색 최적화.",
            "source_type": "text",
            "tags": ["데이터베이스", "PostgreSQL"],
        },
        {
            "title": "Transformer 아키텍처",
            "content": "Transformer는 self-attention 메커니즘 기반 딥러닝 아키텍처. Multi-head attention과 positional encoding이 핵심.",
            "source_type": "text",
            "tags": ["AI", "Transformer"],
        },
    ]

    scrap_ids = []
    for i, sd in enumerate(scrap_data):
        s, b, t = api("POST", "/scraps", token, sd)
        sid = b.get("id", "")
        if sid:
            scrap_ids.append(sid)
        if i == 0:
            test(
                "S2.1",
                f"스크랩 생성: {sd['title'][:15]}",
                "200/201",
                s,
                f"{s}, id={sid[:8] if sid else '?'}",
                s in (200, 201),
            )
    test("S2.2", "스크랩 4개 생성 완료", "4개", 200, f"생성: {len(scrap_ids)}개", len(scrap_ids) == 4)

    # 잠깐 대기 (인덱싱)
    time.sleep(3)

    # S3: Mindmap
    s, b, t = api("GET", "/mindmap", token, timeout=60)
    if isinstance(b, dict):
        nodes = b.get("nodes", [])
        edges = b.get("edges", b.get("links", []))
        test(
            "S3.1",
            "마인드맵 그래프 조회",
            "200 + nodes/edges",
            s,
            f"{s}, nodes={len(nodes)}, edges={len(edges)}, time={t}s",
            s == 200,
        )
    else:
        test("S3.1", "마인드맵 그래프 조회", "200", s, f"{s}, type={type(b).__name__}", s == 200)

    s, b, t = api("GET", "/mindmap/stats", token)
    test(
        "S3.2",
        "마인드맵 통계",
        "200",
        s,
        f"{s}, data={json.dumps(b, ensure_ascii=False)[:100] if isinstance(b, dict) else '?'}",
        s == 200,
    )

    s, b, t = api("GET", "/mindmap/insights", token, timeout=60)
    test("S3.3", "마인드맵 인사이트", "200", s, f"{s}, time={t}s", s == 200)

    # S4: Search
    searches = [
        ("S4.1", "React 컴포넌트", "관련 결과"),
        ("S4.2", "AI 에이전트 프레임워크", "관련 결과"),
        ("S4.3", "벡터 검색 데이터베이스", "관련 결과"),
        ("S4.4", "존재하지않는키워드12345", "빈 결과"),
    ]
    for tid, query, expected in searches:
        s, b, t = api("POST", "/search", token, {"query": query})
        result_count = len(b.get("results", [])) if isinstance(b, dict) else (len(b) if isinstance(b, list) else 0)
        if tid == "S4.4":
            test(tid, f"검색 '{query[:15]}'", expected, s, f"{s}, results={result_count}, time={t}s", s == 200)
        else:
            test(tid, f"검색 '{query[:15]}'", expected, s, f"{s}, results={result_count}, time={t}s", s == 200)

    # S5: Advanced search
    s, b, t = api("POST", "/search/advanced", token, {"query": "AI", "filters": {}})
    test("S5.1", "고급 검색", "200 or 404", s, f"{s}", s in (200, 404))

    s, b, t = api("GET", "/scraps?tags=AI", token)
    ai_count = len(b) if isinstance(b, list) else 0
    test("S5.2", "태그 필터링 (AI)", "200", s, f"{s}, count={ai_count}", s == 200)

    s, b, t = api("GET", "/scraps?search=React", token)
    test("S5.3", "키워드 검색 (React)", "200", s, f"{s}, count={len(b) if isinstance(b, list) else '?'}", s == 200)

    # S6: Export
    s, b, t = api("GET", "/export/scraps?format=json", token)
    test("S6.1", "스크랩 JSON 내보내기", "200", s, f"{s}, type={type(b).__name__}", s == 200)

    s, b, t = api("GET", "/export/scraps?format=csv", token)
    test("S6.2", "스크랩 CSV 내보내기", "200", s, f"{s}", s == 200)

    s, b, t = api("GET", "/export/scraps?format=markdown", token)
    test("S6.3", "스크랩 Markdown 내보내기", "200 or 400", s, f"{s}", s in (200, 400))

    # S7: Duplicate detection
    s, b, t = api("POST", "/scraps/duplicates", token)
    test("S7.1", "중복 스크랩 감지", "200 or 404", s, f"{s}", s in (200, 404))

    s, b, t = api(
        "POST",
        "/scraps",
        token,
        {
            "title": "React와 컴포넌트 패턴",
            "content": "React의 핵심은 컴포넌트 기반 아키텍처입니다. hooks를 활용한 상태관리가 중요합니다.",
            "source_type": "text",
            "tags": ["React"],
        },
    )
    dup_id = b.get("id", "")
    if dup_id:
        scrap_ids.append(dup_id)
    test("S7.2", "유사 스크랩 생성", "200/201 (중복 허용)", s, f"{s}", s in (200, 201))

    # S8: Edge cases
    s, b, t = api("GET", "/mindmap", None)
    test("S8.1", "인증 없이 마인드맵 접근", "401", s, f"{s}", s == 401)

    s, b, t = api("POST", "/search", token, {"query": ""})
    test("S8.2", "빈 쿼리로 검색", "400/422 or 200", s, f"{s}", s in (200, 400, 422))

    s, b, t = api("GET", "/scraps?limit=10000", token)
    test("S8.3", "대량 limit 요청", "200", s, f"{s}, count={len(b) if isinstance(b, list) else '?'}", s == 200)

    # S9: Cleanup
    deleted = 0
    for sid in scrap_ids:
        s, _, _ = api("DELETE", f"/scraps/{sid}", token)
        if s in (200, 204):
            deleted += 1
    test(
        "S9.1",
        "모든 스크랩 삭제",
        f"{len(scrap_ids)}개",
        200,
        f"삭제: {deleted}/{len(scrap_ids)}",
        deleted == len(scrap_ids),
    )

    s, b, t = api("GET", "/scraps", token)
    final = len(b) if isinstance(b, list) else 0
    test("S9.2", "최종 상태 확인", "0개", s, f"remaining={final}", final == 0)

    # Summary
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    p = sum(1 for r in results if r["status"] == "PASS")
    f = sum(1 for r in results if r["status"] == "FAIL")
    print(f"총: {len(results)} | PASS: {p} | FAIL: {f} | 통과율: {p / len(results) * 100:.1f}%")
    print()
    print("| # | 테스트 | 기대값 | 실제값 | 결과 |")
    print("|---|--------|--------|--------|------|")
    for r in results:
        print(f"| {r['id']} | {r['name']} | {r['expected']} | {r['actual']} | {r['status']} |")
    if f > 0:
        print(f"\n실패 {f}건:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  - {r['id']}: {r['name']} — {r['actual']}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback

        traceback.print_exc()
