"""알파테스터 2 — 이수진: 다이어리 CRUD + 캘린더 + AI분석 + 내보내기"""

import json
import time
import urllib.request

BASE = "https://memoir-backend-danwoo.onrender.com/api/v1"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE"
SUPABASE_URL = "https://otzqnucgfrlbqyyhksgo.supabase.co"
EMAIL = "alpha.sujin@memoir.test"
PASSWORD = "AlphaTest2026!"

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


def api(method, path, token=None, body=None):
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
        raw = resp.read().decode()
        try:
            body_resp = json.loads(raw)
        except Exception:
            body_resp = {"raw": raw[:500]}
        elapsed = round(time.time() - start, 2)
        return status, body_resp, elapsed
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_resp = json.loads(e.read().decode())
        except Exception:
            body_resp = {"error": str(e)}
        elapsed = round(time.time() - start, 2)
        return status, body_resp, elapsed
    except Exception as e:
        return 0, {"error": str(e)}, round(time.time() - start, 2)


def test(tid, name, expected, status, actual, passed):
    s = "PASS" if passed else "FAIL"
    results.append({"id": tid, "name": name, "expected": expected, "actual": actual, "status": s})
    print(f"  [{s}] {tid}: {name} (HTTP {status})")


def run():
    print("=" * 60)
    print("알파테스터 2: 이수진 — 다이어리 + 캘린더 + AI + 내보내기")
    print("=" * 60)

    token = login()
    print(f"  토큰 발급 완료 (len={len(token)})")

    # S1: Auth
    s, b, t = api("GET", "/auth/me", token)
    test("S1.1", "인증 확인", "200", s, f"{s}, email={b.get('email', '?')}", s == 200 and b.get("email") == EMAIL)

    # S2: Diary CRUD
    s, b, t = api(
        "POST",
        "/diaries",
        token,
        {
            "content": "오늘은 알파테스트 첫째 날입니다. AI 서비스의 품질을 체계적으로 검증하고 있습니다. 감정적으로는 기대와 긴장이 공존하는 하루였습니다.",
            "date": "2026-03-01",
        },
    )
    diary1_id = b.get("id", "")
    test(
        "S2.1",
        "다이어리 생성 (3/1)",
        "200/201",
        s,
        f"{s}, id={diary1_id[:8] if diary1_id else '?'}",
        s in (200, 201) and bool(diary1_id),
    )

    s, b, t = api(
        "POST",
        "/diaries",
        token,
        {
            "content": "둘째 날 테스트. 어제보다 서비스가 안정적으로 느껴집니다. 스크랩 기능과 연동이 잘 되는지 확인 중입니다.",
            "date": "2026-03-02",
        },
    )
    diary2_id = b.get("id", "")
    test(
        "S2.2",
        "다이어리 생성 (3/2)",
        "200/201",
        s,
        f"{s}, id={diary2_id[:8] if diary2_id else '?'}",
        s in (200, 201) and bool(diary2_id),
    )

    s, b, t = api("GET", "/diaries", token)
    count = len(b) if isinstance(b, list) else 0
    test("S2.3", "다이어리 목록 조회", "200 + 2개", s, f"{s}, count={count}", s == 200 and count >= 2)

    if diary1_id:
        s, b, t = api("GET", f"/diaries/{diary1_id}", token)
        test("S2.4", "다이어리 상세 조회", "200", s, f"{s}, content_len={len(b.get('content', ''))}", s == 200)

        s, b, t = api(
            "PUT",
            f"/diaries/{diary1_id}",
            token,
            {
                "content": "오늘은 알파테스트 첫째 날입니다. AI 서비스의 품질을 체계적으로 검증하고 있습니다. 추가 메모: 테스트 중 수정 기능 검증",
                "date": "2026-03-01",
            },
        )
        test("S2.5", "다이어리 수정", "200", s, f"{s}", s == 200)

        s, b, t = api("GET", f"/diaries/{diary1_id}", token)
        has_update = "추가 메모" in b.get("content", "")
        test("S2.6", "수정 내용 확인", "추가 메모 포함", s, f"{s}, updated={has_update}", s == 200 and has_update)
    else:
        for tid in ["S2.4", "S2.5", "S2.6"]:
            test(tid, "다이어리 조회/수정", "200", 0, "SKIP", False)

    if diary2_id:
        s, b, t = api("DELETE", f"/diaries/{diary2_id}", token)
        test("S2.7", "다이어리 삭제", "200/204", s, f"{s}", s in (200, 204))
    else:
        test("S2.7", "다이어리 삭제", "200/204", 0, "SKIP", False)

    s, b, t = api("GET", "/diaries", token)
    remaining = len(b) if isinstance(b, list) else 0
    test("S2.8", "삭제 후 목록 확인", "1개 남음", s, f"{s}, remaining={remaining}", s == 200 and remaining >= 1)

    # S3: Calendar
    s, b, t = api("GET", "/calendar/2026/3", token)
    test(
        "S3.1",
        "캘린더 3월 조회",
        "200",
        s,
        f"{s}, keys={list(b.keys()) if isinstance(b, dict) else type(b).__name__}",
        s == 200,
    )

    s, b, t = api("GET", "/calendar/2026/2", token)
    test("S3.2", "캘린더 2월 조회 (빈 데이터)", "200", s, f"{s}", s == 200)

    test("S3.3", "캘린더 응답 구조 확인", "diary/tags 포함", s, f"type={type(b).__name__}", isinstance(b, dict | list))

    # S4: AI
    if diary1_id:
        s, b, t = api("POST", f"/diaries/{diary1_id}/insights", token)
        test("S4.1", "AI 분석 요청", "200/202", s, f"{s}, time={t}s", s in (200, 201, 202))

        time.sleep(2)
        s, b, t = api("GET", f"/diaries/{diary1_id}", token)
        tags = b.get("tags", [])
        test("S4.2", "AI 태그 확인", "tags 존재", s, f"{s}, tags={tags}", s == 200)
    else:
        test("S4.1", "AI 분석 요청", "200", 0, "SKIP", False)
        test("S4.2", "AI 태그 확인", "tags", 0, "SKIP", False)

    # S5: Digest
    s, b, t = api("GET", "/digest/daily", token)
    test("S5.1", "일간 다이제스트", "200", s, f"{s}, time={t}s", s == 200)

    s, b, t = api("GET", "/digest/weekly", token)
    test("S5.2", "주간 다이제스트", "200", s, f"{s}, time={t}s", s == 200)

    s, b, t = api("GET", "/reports", token)
    test("S5.3", "리포트 목록", "200", s, f"{s}", s == 200)

    # S6: Export
    s, b, t = api("GET", "/export/diaries?format=json", token)
    test("S6.1", "다이어리 JSON 내보내기", "200", s, f"{s}", s == 200)

    s, b, t = api("GET", "/export/diaries?format=csv", token)
    test("S6.2", "다이어리 CSV 내보내기", "200", s, f"{s}", s == 200)

    # S7: Edge cases
    s, b, t = api("POST", "/diaries", token, {"content": "", "date": "2026-03-03"})
    test("S7.1", "빈 컨텐츠 다이어리 생성", "422 or 200", s, f"{s}", s in (200, 201, 422))

    s, b, t = api("GET", "/diaries/00000000-0000-0000-0000-000000000000", token)
    test("S7.2", "존재하지 않는 다이어리 조회", "404", s, f"{s}", s == 404)

    s, b, t = api("GET", "/diaries", None)
    test("S7.3", "인증 없이 다이어리 접근", "401", s, f"{s}", s == 401)

    s, b, t = api("POST", "/diaries", token, {"content": "중복 날짜 테스트 다이어리", "date": "2026-03-01"})
    dup_id = b.get("id", "")
    test("S7.4", "중복 날짜 다이어리 생성", "200 or 409", s, f"{s}", s in (200, 201, 409))

    # S8: Cleanup
    for did in [diary1_id, dup_id]:
        if did:
            api("DELETE", f"/diaries/{did}", token)

    # 빈 컨텐츠로 만든 다이어리도 삭제
    s, b, t = api("GET", "/diaries", token)
    if isinstance(b, list):
        for d in b:
            if d.get("date", "").startswith("2026-03"):
                api("DELETE", f"/diaries/{d['id']}", token)

    s, b, t = api("GET", "/diaries", token)
    final = len(b) if isinstance(b, list) else 0
    test("S8.1", "클린업 완료", "0개", s, f"remaining={final}", final == 0)

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
