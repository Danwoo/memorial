"""헬스 엔드포인트 + request_id 미들웨어 통합 테스트."""

from __future__ import annotations


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_echoes_request_id_header(client):
    """upstream에서 X-Request-ID를 넘기면 response에 그대로 echo."""
    response = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "trace-abc-123"


def test_health_assigns_new_request_id_when_missing(client):
    """X-Request-ID 미제공 시 새로 생성하여 응답 헤더에 부착."""
    response = client.get("/health")
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    assert rid != "-"
    assert len(rid) == 12  # new_request_id() 정책


def test_health_rejects_overly_long_external_request_id(client):
    """64자 초과 X-Request-ID는 폐기하고 새로 생성 (injection 방어)."""
    long_rid = "a" * 200
    response = client.get("/health", headers={"X-Request-ID": long_rid})
    assert response.headers.get("X-Request-ID") != long_rid
