"""알파테스터 3 — 박현우: Socrates 채팅 세션 + 멀티 모드 + 피드백"""

import json
import time
import urllib.request

BASE = "https://memoir-backend-danwoo.onrender.com/api/v1"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90enFudWNnZnJsYnF5eWhrc2dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3NjE5NjQsImV4cCI6MjA4NTMzNzk2NH0.ewsd_uZl7hkjdH9Np-P03J0R4qJT6-H1natMKUIy8zE"
SUPABASE_URL = "https://otzqnucgfrlbqyyhksgo.supabase.co"
EMAIL = "alpha.hyunwoo@memoir.test"
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
            body_resp = {"raw": raw[:1000]}
        elapsed = round(time.time() - start, 2)
        return status, body_resp, elapsed
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_resp = json.loads(e.read().decode())
        except Exception:
            body_resp = {"error": str(e)}
        return status, body_resp, round(time.time() - start, 2)
    except Exception as e:
        return 0, {"error": str(e)}, round(time.time() - start, 2)


def api_sse(path, token, body, timeout=60):
    """SSE 스트리밍 엔드포인트용"""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream", "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    start = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        status = resp.status
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read().decode()
        elapsed = round(time.time() - start, 2)

        if "event-stream" in content_type or raw.startswith("data:"):
            events = []
            for line in raw.split("\n"):
                if line.startswith("data:"):
                    try:
                        events.append(json.loads(line[5:].strip()))
                    except Exception:
                        events.append({"raw": line[5:].strip()})
            return status, {"events": events, "event_count": len(events)}, elapsed
        else:
            try:
                return status, json.loads(raw), elapsed
            except Exception:
                return status, {"raw": raw[:1000]}, elapsed
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
    print("알파테스터 3: 박현우 — Socrates 채팅 + 세션 관리")
    print("=" * 60)

    token = login()
    print("  토큰 발급 완료")

    # S1: Auth
    s, b, t = api("GET", "/auth/me", token)
    test("S1.1", "인증 확인", "200", s, f"{s}, email={b.get('email', '?')}", s == 200)

    # S2: Session Management
    s, b, t = api("POST", "/socrates/sessions", token, {"title": "알파테스트 대화"})
    session_id = b.get("id", "") or b.get("session_id", "")
    test(
        "S2.1",
        "세션 생성",
        "200/201",
        s,
        f"{s}, id={session_id[:8] if session_id else '?'}",
        s in (200, 201) and bool(session_id),
    )

    s, b, t = api("GET", "/socrates/sessions", token)
    session_count = len(b) if isinstance(b, list) else 0
    test("S2.2", "세션 목록 조회", "200 + 1개 이상", s, f"{s}, count={session_count}", s == 200 and session_count >= 1)

    if session_id:
        s, b, t = api("GET", f"/socrates/sessions/{session_id}", token)
        test("S2.3", "세션 상세 조회", "200", s, f"{s}, title={b.get('title', '?')}", s == 200)

        s, b, t = api("PUT", f"/socrates/sessions/{session_id}", token, {"title": "수정된 대화 제목"})
        test("S2.4", "세션 제목 수정", "200", s, f"{s}", s == 200)

        s, b, t = api("GET", f"/socrates/sessions/{session_id}", token)
        title = b.get("title", "")
        test("S2.5", "수정 확인", "수정된 대화 제목", s, f"{s}, title={title}", s == 200 and "수정" in title)
    else:
        for tid in ["S2.3", "S2.4", "S2.5"]:
            test(tid, "세션 관리", "200", 0, "SKIP (no session)", False)

    # S3: Chat (SSE streaming)
    if session_id:
        print("\n  [SSE 채팅 테스트 시작 — 각 요청 최대 60초 대기]")

        s, b, t = api_sse(
            "/socrates/chat",
            token,
            {"message": "안녕하세요, 저는 알파테스터 현우입니다.", "session_id": session_id, "mode": "default"},
            timeout=60,
        )
        test("S3.1", "기본 모드 대화", "200 + 응답", s, f"{s}, time={t}s, type={type(b).__name__}", s == 200)

        s, b, t = api_sse(
            "/socrates/chat",
            token,
            {"message": "AI 기술 발전이 빨라서 불안합니다.", "session_id": session_id, "mode": "insight"},
            timeout=60,
        )
        test("S3.2", "인사이트 모드", "200", s, f"{s}, time={t}s", s == 200)

        s, b, t = api_sse(
            "/socrates/chat",
            token,
            {"message": "AI가 일자리를 완전히 대체할 것입니다.", "session_id": session_id, "mode": "counter"},
            timeout=60,
        )
        test("S3.3", "반론 모드", "200", s, f"{s}, time={t}s", s == 200)

        s, b, t = api_sse(
            "/socrates/chat",
            token,
            {"message": "대화를 정리해주세요", "session_id": session_id, "mode": "summary"},
            timeout=60,
        )
        test("S3.4", "요약 모드", "200", s, f"{s}, time={t}s", s == 200)
    else:
        for tid in ["S3.1", "S3.2", "S3.3", "S3.4"]:
            test(tid, "채팅", "200", 0, "SKIP", False)

    # S4: Additional modes
    if session_id:
        for mode_info in [
            ("S4.1", "evening_review", "저녁 회고 모드"),
            ("S4.2", "full_analysis", "전체 분석 모드"),
            ("S4.3", "five_why", "5 Why 모드"),
        ]:
            tid, mode, name = mode_info
            s, b, t = api_sse(
                "/socrates/chat",
                token,
                {"message": "이 모드를 테스트합니다.", "session_id": session_id, "mode": mode},
                timeout=60,
            )
            test(tid, name, "200", s, f"{s}, time={t}s", s == 200)
    else:
        for tid in ["S4.1", "S4.2", "S4.3"]:
            test(tid, "추가 모드", "200", 0, "SKIP", False)

    # S5: Messages & Feedback
    if session_id:
        s, b, t = api("GET", f"/socrates/sessions/{session_id}/messages", token)
        msg_count = len(b) if isinstance(b, list) else 0
        test("S5.1", "메시지 목록 조회", "200 + 메시지 존재", s, f"{s}, messages={msg_count}", s == 200)

        msg_id = None
        if isinstance(b, list) and len(b) > 0:
            msg_id = b[0].get("id", "")

        if msg_id:
            s, b, t = api(
                "POST",
                "/socrates/feedback",
                token,
                {"message_id": msg_id, "helpful": True, "comment": "도움이 되었습니다"},
            )
            test("S5.2", "피드백 제출", "200/201", s, f"{s}", s in (200, 201))
        else:
            test("S5.2", "피드백 제출", "200", 0, "SKIP (no msg)", False)

        s, b, t = api("GET", f"/socrates/sessions/{session_id}/messages", token)
        test(
            "S5.3", "메시지 지속성 확인", "200", s, f"{s}, messages={len(b) if isinstance(b, list) else '?'}", s == 200
        )
    else:
        for tid in ["S5.1", "S5.2", "S5.3"]:
            test(tid, "메시지/피드백", "200", 0, "SKIP", False)

    # S6: Session cleanup
    if session_id:
        s, b, t = api("DELETE", f"/socrates/sessions/{session_id}", token)
        test("S6.1", "세션 삭제", "200/204", s, f"{s}", s in (200, 204))

        s, b, t = api("GET", "/socrates/sessions", token)
        remaining = len(b) if isinstance(b, list) else 0
        test("S6.2", "삭제 확인", "0개", s, f"remaining={remaining}", remaining == 0)
    else:
        test("S6.1", "세션 삭제", "200", 0, "SKIP", False)
        test("S6.2", "삭제 확인", "0", 0, "SKIP", False)

    # S7: Edge cases
    s, b, t = api_sse("/socrates/chat", token, {"message": "세션 없이 채팅", "mode": "default"}, timeout=30)
    test("S7.1", "session_id 없이 채팅", "400/422", s, f"{s}", s in (400, 422))

    s, b, t = api_sse(
        "/socrates/chat",
        token,
        {"message": "잘못된 모드", "session_id": "00000000-0000-0000-0000-000000000000", "mode": "invalid_mode_xyz"},
        timeout=30,
    )
    test("S7.2", "잘못된 모드로 채팅", "400/422", s, f"{s}", s in (400, 422))

    s, b, t = api("GET", "/socrates/sessions/00000000-0000-0000-0000-000000000000", token)
    test("S7.3", "존재하지 않는 세션 조회", "404", s, f"{s}", s == 404)

    s, b, t = api("GET", "/socrates/sessions", None)
    test("S7.4", "인증 없이 세션 접근", "401", s, f"{s}", s == 401)

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
