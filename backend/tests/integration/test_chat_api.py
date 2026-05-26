"""채팅 세션 API 통합 테스트 — ChatService를 mock하여 router contract 검증."""

from __future__ import annotations

from tests.integration.conftest import SESSION_ID, make_chat_service_mock


def test_create_session(client):
    from app.config.dependencies import get_chat_service
    from app.main import app

    svc = make_chat_service_mock()
    app.dependency_overrides[get_chat_service] = lambda: svc

    response = client.post(
        "/api/v1/socrates/sessions",
        json={"title": "Test Session", "agent_type": "oracle"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(SESSION_ID)
    assert data["title"] == "Test Session"
    assert data["agent_type"] == "oracle"
    svc.create_session.assert_called_once()


def test_list_sessions(client):
    from app.config.dependencies import get_chat_service
    from app.main import app

    svc = make_chat_service_mock()
    app.dependency_overrides[get_chat_service] = lambda: svc

    response = client.get("/api/v1/socrates/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["id"] == str(SESSION_ID)


def test_get_history(client):
    from app.config.dependencies import get_chat_service
    from app.main import app

    svc = make_chat_service_mock()
    app.dependency_overrides[get_chat_service] = lambda: svc

    response = client.get(f"/api/v1/socrates/sessions/{SESSION_ID}/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_get_history_404_when_session_not_found(client):
    from app.config.dependencies import get_chat_service
    from app.main import app

    svc = make_chat_service_mock()
    svc.get_session.return_value = None
    app.dependency_overrides[get_chat_service] = lambda: svc

    response = client.get(f"/api/v1/socrates/sessions/{SESSION_ID}/history")
    assert response.status_code == 404


def test_update_session_title(client):
    from app.config.dependencies import get_chat_service
    from app.main import app

    svc = make_chat_service_mock()
    app.dependency_overrides[get_chat_service] = lambda: svc

    response = client.patch(
        f"/api/v1/socrates/sessions/{SESSION_ID}",
        json={"title": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"
    svc.update_session_title.assert_called_once()


def test_add_feedback(client):
    from app.config.dependencies import get_chat_service
    from app.main import app

    svc = make_chat_service_mock()
    app.dependency_overrides[get_chat_service] = lambda: svc

    response = client.post(
        f"/api/v1/socrates/sessions/{SESSION_ID}/feedback",
        json={"message_index": 0, "rating": "good"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}
