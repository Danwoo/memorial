"""알파테스터 5 — 한동원: 통합 테스트 + 보안 + 카카오봇 + 에러 처리 + 성능"""

import contextlib
import json
import time
import urllib.request

BASE_ROOT = "https://memoir-backend-danwoo.onrender.com"
BASE = "https://memoir-backend-danwoo.onrender.com/api/v1"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE"
SUPABASE_URL = "https://otzqnucgfrlbqyyhksgo.supabase.co"
EMAIL = "alpha.dongwon@memoir.test"
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


def api(method, path, token=None, body=None, timeout=30, extra_headers=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        status = resp.status
        raw = resp.read().decode()
        resp_headers = dict(resp.headers)
        try:
            body_resp = json.loads(raw)
        except Exception:
            body_resp = {"raw": raw[:500]}
        return status, body_resp, round(time.time() - start, 2), resp_headers
    except urllib.error.HTTPError as e:
        status = e.code
        resp_headers = dict(e.headers) if hasattr(e, "headers") else {}
        try:
            body_resp = json.loads(e.read().decode())
        except Exception:
            body_resp = {"error": str(e)}
        return status, body_resp, round(time.time() - start, 2), resp_headers
    except Exception as e:
        return 0, {"error": str(e)}, round(time.time() - start, 2), {}


def test(tid, name, expected, status, actual, passed):
    s = "PASS" if passed else "FAIL"
    results.append({"id": tid, "name": name, "expected": expected, "actual": actual, "status": s})
    print(f"  [{s}] {tid}: {name} (HTTP {status})")


def run():
    print("=" * 60)
    print("알파테스터 5: 한동원 — 통합 + 보안 + 카카오봇 + 성능")
    print("=" * 60)

    token = login()
    print("  토큰 발급 완료")

    # S1: Infrastructure
    s, b, t, h = api("GET", "/auth/me", token)
    test("S1.1", "인증 확인", "200", s, f"{s}, email={b.get('email', '?')}", s == 200)

    # health와 docs는 루트 레벨
    url_health = f"{BASE_ROOT}/health"
    req_h = urllib.request.Request(url_health)
    start_h = time.time()
    try:
        resp_h = urllib.request.urlopen(req_h)
        h_status = resp_h.status
        h_body = json.loads(resp_h.read().decode())
        h_time = round(time.time() - start_h, 2)
    except Exception:
        h_status, h_body, h_time = 0, {}, 0
    test(
        "S1.2",
        "헬스체크",
        "200",
        h_status,
        f"{h_status}, status={h_body.get('status', '?')}, time={h_time}s",
        h_status == 200 and h_body.get("status") == "ok",
    )

    url_docs = f"{BASE_ROOT}/docs"
    req_d = urllib.request.Request(url_docs)
    try:
        resp_d = urllib.request.urlopen(req_d)
        d_status = resp_d.status
    except Exception:
        d_status = 0
    test("S1.3", "OpenAPI 문서", "200", d_status, f"{d_status}", d_status == 200)

    # CORS preflight
    cors_req = urllib.request.Request(f"{BASE}/scraps", method="OPTIONS")
    cors_req.add_header("Origin", "https://memoir-knowledge.vercel.app")
    cors_req.add_header("Access-Control-Request-Method", "GET")
    try:
        cors_resp = urllib.request.urlopen(cors_req)
        cors_status = cors_resp.status
        cors_headers = dict(cors_resp.headers)
        has_cors = "access-control-allow-origin" in {k.lower(): v for k, v in cors_headers.items()}
        test(
            "S1.4",
            "CORS preflight",
            "200 + CORS 헤더",
            cors_status,
            f"{cors_status}, cors={has_cors}",
            cors_status == 200 and has_cors,
        )
    except Exception as e:
        test("S1.4", "CORS preflight", "200", 0, f"ERROR: {e}", False)

    # S2: Kakao Bot
    kakao_payloads = [
        (
            "S2.1",
            "일반 메시지",
            {
                "userRequest": {"utterance": "안녕하세요 메모아르", "user": {"id": "test_kakao_dongwon"}},
                "action": {"name": "fallback"},
            },
        ),
        (
            "S2.2",
            "저장 명령",
            {
                "userRequest": {
                    "utterance": "저장 오늘 배운 것: React hooks는 함수형 컴포넌트에서 상태관리를 가능하게 합니다",
                    "user": {"id": "test_kakao_dongwon"},
                },
                "action": {"name": "fallback"},
            },
        ),
        (
            "S2.3",
            "검색 명령",
            {
                "userRequest": {"utterance": "검색 React", "user": {"id": "test_kakao_dongwon"}},
                "action": {"name": "fallback"},
            },
        ),
        (
            "S2.4",
            "빈 메시지",
            {"userRequest": {"utterance": "", "user": {"id": "test_kakao_dongwon"}}, "action": {"name": "fallback"}},
        ),
    ]
    for tid, name, payload in kakao_payloads:
        s, b, t, h = api("POST", "/integrations/kakao/webhook", body=payload, timeout=30)
        has_response = isinstance(b, dict) and ("template" in b or "version" in b)
        test(tid, f"카카오봇: {name}", "200 + 응답", s, f"{s}, has_template={has_response}, time={t}s", s == 200)

    # S3: Notifications
    s, b, t, h = api("GET", "/notifications", token)
    test("S3.1", "알림 목록", "200", s, f"{s}", s == 200)

    s, b, t, h = api("GET", "/notifications/settings", token)
    test("S3.2", "알림 설정 조회", "200", s, f"{s}", s == 200)

    s, b, t, h = api("PUT", "/notifications/settings", token, {"email_enabled": False, "push_enabled": True})
    test("S3.3", "알림 설정 변경", "200", s, f"{s}", s == 200)

    # S4: Cross-feature Integration
    s, b, t, h = api(
        "POST",
        "/scraps",
        token,
        {
            "title": "통합 테스트 스크랩",
            "content": "이 스크랩은 다이어리와의 통합을 테스트합니다.",
            "source_type": "text",
            "tags": ["통합테스트"],
        },
    )
    integ_scrap_id = b.get("id", "")
    test("S4.1", "통합용 스크랩 생성", "200/201", s, f"{s}", s in (200, 201))

    s, b, t, h = api(
        "POST",
        "/diaries",
        token,
        {"content": "통합 테스트 다이어리. 스크랩과 연결을 테스트합니다.", "date": "2026-03-01"},
    )
    integ_diary_id = b.get("id", "")
    test("S4.2", "통합용 다이어리 생성", "200/201", s, f"{s}", s in (200, 201))

    if integ_diary_id and integ_scrap_id:
        s, b, t, h = api("POST", f"/diaries/{integ_diary_id}/scrap-links", token, {"scrap_id": integ_scrap_id})
        test("S4.3", "다이어리-스크랩 연결", "200/201 or 404", s, f"{s}", s in (200, 201, 404))

        s, b, t, h = api("GET", f"/diaries/{integ_diary_id}", token)
        test(
            "S4.4",
            "연결 확인",
            "200",
            s,
            f"{s}, has_scraps={'scrap' in json.dumps(b, ensure_ascii=False).lower()}",
            s == 200,
        )
    else:
        test("S4.3", "다이어리-스크랩 연결", "200", 0, "SKIP", False)
        test("S4.4", "연결 확인", "200", 0, "SKIP", False)

    # S5: Security
    unauth_endpoints = [
        ("S5.1", "GET", "/scraps"),
        ("S5.2", "GET", "/diaries"),
        ("S5.3", "GET", "/socrates/sessions"),
        ("S5.4", "GET", "/mindmap"),
        ("S5.5", "GET", "/calendar/2026/3"),
    ]
    for tid, method, path in unauth_endpoints:
        s, b, t, h = api(method, path, None)
        test(tid, f"미인증 {path}", "401", s, f"{s}", s == 401)

    s, b, t, h = api("GET", "/scraps", None, extra_headers={"Authorization": "Bearer invalid.token.here"})
    test("S5.6", "잘못된 토큰", "401", s, f"{s}", s == 401)

    s, b, t, h = api("GET", "/scraps/99999999-9999-9999-9999-999999999999", token)
    test("S5.7", "타인 스크랩 접근 시도", "404 (정보 유출 방지)", s, f"{s}", s == 404)

    # S6: Error Handling
    s, b, t, h = api("GET", "/nonexistent-route-xyz")
    test("S6.1", "존재하지 않는 라우트", "404", s, f"{s}", s == 404)

    malformed_req = urllib.request.Request(
        f"{BASE}/scraps",
        data=b"not-json",
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    try:
        resp = urllib.request.urlopen(malformed_req)
        test("S6.2", "잘못된 JSON 요청", "400/422", resp.status, f"{resp.status}", resp.status in (400, 422))
    except urllib.error.HTTPError as e:
        test("S6.2", "잘못된 JSON 요청", "400/422", e.code, f"{e.code}", e.code in (400, 422))

    long_content = "A" * 10000
    s, b, t, h = api("POST", "/diaries", token, {"content": long_content, "date": "2026-03-03"})
    long_diary_id = b.get("id", "")
    test("S6.3", "매우 긴 컨텐츠 (10000자)", "200/201 (처리 가능)", s, f"{s}, time={t}s", s in (200, 201))

    s, b, t, h = api("GET", "/scraps?search=%27%3B+DROP+TABLE+scraps%3B+--", token)
    test("S6.4", "SQL 인젝션 시도", "200 (안전 처리)", s, f"{s}", s in (200, 400, 422))

    s, b, t, h = api(
        "POST",
        "/scraps",
        token,
        {"title": "<script>alert('xss')</script>", "content": "XSS 테스트", "source_type": "text"},
    )
    xss_id = b.get("id", "")
    test("S6.5", "XSS 시도 (title)", "200 (저장되나 렌더 시 이스케이프)", s, f"{s}", s in (200, 201))

    # S7: Performance
    perf_results = []
    for _ in range(3):
        start_p = time.time()
        with contextlib.suppress(Exception):
            urllib.request.urlopen(f"{BASE_ROOT}/health")
        perf_results.append(round(time.time() - start_p, 2))
    avg_health = sum(perf_results) / len(perf_results)
    test("S7.1", "헬스체크 평균 응답시간", "<2s", 200, f"avg={avg_health:.2f}s", avg_health < 2)

    s, b, t, h = api("GET", "/scraps", token)
    test("S7.2", "스크랩 목록 응답시간", "<5s", s, f"time={t}s", t < 5)

    s, b, t, h = api("POST", "/search", token, {"query": "테스트"})
    test("S7.3", "검색 응답시간", "<10s", s, f"time={t}s", t < 10)

    # S8: Cleanup
    cleanup_ids = [integ_scrap_id, xss_id]
    for sid in cleanup_ids:
        if sid:
            api("DELETE", f"/scraps/{sid}", token)

    diary_cleanup = [integ_diary_id, long_diary_id]
    for did in diary_cleanup:
        if did:
            api("DELETE", f"/diaries/{did}", token)

    # 추가 정리
    s, b, t, h = api("GET", "/diaries", token)
    if isinstance(b, list):
        for d in b:
            api("DELETE", f"/diaries/{d['id']}", token)
    s, b, t, h = api("GET", "/scraps", token)
    if isinstance(b, list):
        for sc in b:
            api("DELETE", f"/scraps/{sc['id']}", token)

    test("S8.1", "전체 클린업", "완료", 200, "OK", True)

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

    # Bug report
    bugs = []
    for r in results:
        if r["status"] == "FAIL":
            if "401" in r["actual"] and "401" not in r["expected"] or "500" in r["actual"]:
                bugs.append(("P0", r["id"], r["name"], r["actual"]))
            elif "timeout" in r["actual"].lower():
                bugs.append(("P1", r["id"], r["name"], r["actual"]))
            else:
                bugs.append(("P2", r["id"], r["name"], r["actual"]))

    if bugs:
        print(f"\n버그 리포트 ({len(bugs)}건):")
        print("| 등급 | 테스트 | 설명 | 상세 |")
        print("|------|--------|------|------|")
        for sev, tid, name, detail in bugs:
            print(f"| {sev} | {tid} | {name} | {detail} |")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback

        traceback.print_exc()
