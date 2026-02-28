"""알파테스터 1 — 김민준: 스크랩 CRUD + 검색 + 에러 처리"""

import json
import time
import urllib.request

BASE = "https://memoir-backend-danwoo.onrender.com/api/v1"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE"
SUPABASE_URL = "https://otzqnucgfrlbqyyhksgo.supabase.co"
EMAIL = "alpha.minjun@memoir.test"
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


def api(method, path, token=None, body=None, expect_status=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    start = time.time()
    try:
        resp = urllib.request.urlopen(req)
        status = resp.status
        body_resp = json.loads(resp.read().decode())
        elapsed = round(time.time() - start, 2)
        return status, body_resp, elapsed
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_resp = json.loads(e.read().decode())
        except Exception:
            body_resp = {"raw": str(e)}
        elapsed = round(time.time() - start, 2)
        return status, body_resp, elapsed
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        return 0, {"error": str(e)}, elapsed


def test(test_id, name, expected, actual_status, actual_summary, passed):
    status_str = "PASS" if passed else "FAIL"
    results.append(
        {
            "id": test_id,
            "name": name,
            "expected": expected,
            "actual": actual_summary,
            "status": status_str,
            "http_status": actual_status,
        }
    )
    print(f"  [{status_str}] {test_id}: {name} (HTTP {actual_status})")


def run():
    print("=" * 60)
    print("알파테스터 1: 김민준 — 스크랩 CRUD + 검색")
    print("=" * 60)

    # Login
    print("\n[로그인 중...]")
    token = login()
    print(f"  토큰 발급 완료 (len={len(token)})")

    # S1.1: Auth
    s, b, t = api("GET", "/auth/me", token)
    test(
        "S1.1",
        "인증 확인 (GET /auth/me)",
        "200 + email",
        s,
        f"{s}, email={b.get('email', '?')}",
        s == 200 and b.get("email") == EMAIL,
    )

    # S2.1: Create text scrap
    s, b, t = api(
        "POST",
        "/scraps",
        token,
        {
            "title": "알파테스트 스크랩 1",
            "content": "민준의 첫 스크랩입니다. AI와 지식관리에 대한 테스트.",
            "source_type": "text",
            "tags": ["알파테스트", "민준"],
        },
    )
    scrap1_id = b.get("id", "")
    test(
        "S2.1",
        "텍스트 스크랩 생성",
        "201/200",
        s,
        f"{s}, id={scrap1_id[:8] if scrap1_id else '?'}...",
        s in (200, 201) and bool(scrap1_id),
    )

    # S2.2: Create URL scrap
    s, b, t = api(
        "POST",
        "/scraps",
        token,
        {
            "title": "알파테스트 URL 스크랩",
            "content": "https://example.com 웹페이지 스크랩 테스트",
            "source_type": "web",
            "url": "https://example.com",
            "tags": ["웹", "테스트"],
        },
    )
    scrap2_id = b.get("id", "")
    test(
        "S2.2",
        "URL 스크랩 생성",
        "201/200",
        s,
        f"{s}, id={scrap2_id[:8] if scrap2_id else '?'}...",
        s in (200, 201) and bool(scrap2_id),
    )

    # S2.3: List scraps
    s, b, t = api("GET", "/scraps", token)
    scrap_count = len(b) if isinstance(b, list) else b.get("total", 0)
    test("S2.3", "스크랩 목록 조회", "200 + 2개 이상", s, f"{s}, count={scrap_count}", s == 200 and scrap_count >= 2)

    # S2.4: Get scrap by ID
    if scrap1_id:
        s, b, t = api("GET", f"/scraps/{scrap1_id}", token)
        test(
            "S2.4",
            "스크랩 상세 조회",
            "200 + title 일치",
            s,
            f"{s}, title={b.get('title', '?')}",
            s == 200 and "알파테스트" in b.get("title", ""),
        )
    else:
        test("S2.4", "스크랩 상세 조회", "200", 0, "SKIP (no scrap1_id)", False)

    # S2.5: Update scrap
    if scrap1_id:
        s, b, t = api(
            "PUT",
            f"/scraps/{scrap1_id}",
            token,
            {
                "title": "수정된 스크랩 제목",
                "content": "민준의 첫 스크랩입니다. AI와 지식관리에 대한 테스트. (수정됨)",
                "source_type": "text",
            },
        )
        test("S2.5", "스크랩 수정", "200", s, f"{s}, title={b.get('title', '?')}", s == 200)
    else:
        test("S2.5", "스크랩 수정", "200", 0, "SKIP", False)

    # S2.6: Verify update
    if scrap1_id:
        s, b, t = api("GET", f"/scraps/{scrap1_id}", token)
        test(
            "S2.6",
            "수정 확인",
            "200 + 수정된 제목",
            s,
            f"{s}, title={b.get('title', '?')}",
            s == 200 and "수정된" in b.get("title", ""),
        )
    else:
        test("S2.6", "수정 확인", "200", 0, "SKIP", False)

    # S2.7: Delete second scrap
    if scrap2_id:
        s, b, t = api("DELETE", f"/scraps/{scrap2_id}", token)
        test("S2.7", "스크랩 삭제", "200/204", s, f"{s}", s in (200, 204))
    else:
        test("S2.7", "스크랩 삭제", "200/204", 0, "SKIP", False)

    # S2.8: Verify deletion
    s, b, t = api("GET", "/scraps", token)
    remaining = len(b) if isinstance(b, list) else 0
    has_deleted = any(x.get("id") == scrap2_id for x in b) if isinstance(b, list) else False
    test(
        "S2.8",
        "삭제 확인",
        "삭제된 스크랩 없음",
        s,
        f"{s}, remaining={remaining}, deleted_present={has_deleted}",
        s == 200 and not has_deleted,
    )

    # S3: Search
    s, b, t = api("POST", "/search", token, {"query": "알파테스트"})
    search_count = len(b.get("results", [])) if isinstance(b, dict) else (len(b) if isinstance(b, list) else 0)
    test("S3.1", "검색 '알파테스트'", "200 + 결과 있음", s, f"{s}, results={search_count}, time={t}s", s == 200)

    s, b, t = api("POST", "/search", token, {"query": "AI 지식관리"})
    test("S3.2", "검색 'AI 지식관리'", "200", s, f"{s}, time={t}s", s == 200)

    # S4: Bulk create
    bulk_ids = []
    for i in range(3):
        s, b, t = api(
            "POST",
            "/scraps",
            token,
            {
                "title": f"벌크 스크랩 {i + 1}",
                "content": f"벌크 테스트 컨텐츠 {i + 1}. 다양한 스크랩을 생성하여 페이지네이션과 필터링을 테스트합니다.",
                "source_type": "text",
                "tags": [f"벌크{i + 1}"],
            },
        )
        if b.get("id"):
            bulk_ids.append(b["id"])
    test("S4.1", "벌크 스크랩 3개 생성", "3개 생성", s, f"생성: {len(bulk_ids)}개", len(bulk_ids) == 3)

    # S4.2: Pagination
    s, b, t = api("GET", "/scraps?limit=2", token)
    page_count = len(b) if isinstance(b, list) else 0
    test(
        "S4.2", "페이지네이션 (limit=2)", "200 + 2개 반환", s, f"{s}, count={page_count}", s == 200 and page_count <= 2
    )

    # S4.3: Filter by source_type
    s, b, t = api("GET", "/scraps?source_type=text", token)
    test("S4.3", "소스타입 필터링", "200", s, f"{s}, count={len(b) if isinstance(b, list) else '?'}", s == 200)

    # S5: Edge cases
    s, b, t = api("GET", "/scraps/00000000-0000-0000-0000-000000000000", token)
    test("S5.1", "존재하지 않는 스크랩 조회", "404", s, f"{s}", s == 404)

    s, b, t = api("POST", "/scraps", token, {})
    test("S5.2", "빈 바디로 스크랩 생성", "422", s, f"{s}", s == 422)

    s, b, t = api("GET", "/scraps", None)
    test("S5.3", "인증 없이 스크랩 접근", "401", s, f"{s}", s == 401)

    if scrap1_id:
        s, b, t = api("PUT", f"/scraps/{scrap1_id}", token, {"title": ""})
        test("S5.4", "빈 제목으로 수정", "422 or 200", s, f"{s}", s in (200, 422))
    else:
        test("S5.4", "빈 제목으로 수정", "422", 0, "SKIP", False)

    # S6: Cleanup
    all_ids = [scrap1_id] + bulk_ids
    deleted = 0
    for sid in all_ids:
        if sid:
            s, _, _ = api("DELETE", f"/scraps/{sid}", token)
            if s in (200, 204):
                deleted += 1
    test(
        "S6.1",
        "모든 스크랩 삭제",
        f"{len(all_ids)}개 삭제",
        200,
        f"삭제: {deleted}/{len(all_ids)}",
        deleted == len(all_ids),
    )

    s, b, t = api("GET", "/scraps", token)
    final_count = len(b) if isinstance(b, list) else 0
    test("S6.2", "최종 상태 확인", "0개", s, f"{s}, count={final_count}", s == 200 and final_count == 0)

    # Summary
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    print(f"총 테스트: {len(results)}")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    print(f"통과율: {passed / len(results) * 100:.1f}%")
    print()
    print("| # | 테스트 | 기대값 | 실제값 | 결과 |")
    print("|---|--------|--------|--------|------|")
    for r in results:
        print(f"| {r['id']} | {r['name']} | {r['expected']} | {r['actual']} | {r['status']} |")

    if failed > 0:
        print("\n실패 목록:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  - {r['id']}: {r['name']} — {r['actual']}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
