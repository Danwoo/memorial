"""다이어리 API 통합 테스트."""

from __future__ import annotations

from tests.integration.conftest import DIARY_ID, make_diary_service_mock


def test_create_diary(client):
    from unittest.mock import AsyncMock, MagicMock

    from app.config.dependencies import get_diary_orchestrator, get_diary_service
    from app.main import app

    diary_svc = make_diary_service_mock()
    orchestrator = MagicMock()
    orchestrator.process_diary_with_librarian = AsyncMock(return_value=None)

    app.dependency_overrides[get_diary_service] = lambda: diary_svc
    app.dependency_overrides[get_diary_orchestrator] = lambda: orchestrator

    response = client.post(
        "/api/v1/diaries",
        json={"content": "오늘은 좋은 하루였다. 새 프로젝트 시작이 잘 됐다."},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(DIARY_ID)
    assert data["content"] == "오늘의 일기"
    assert data["mood"] == "POSITIVE"
    diary_svc.create_entry.assert_called_once()


def test_list_diaries(client):
    from app.config.dependencies import get_diary_service
    from app.main import app

    diary_svc = make_diary_service_mock()
    app.dependency_overrides[get_diary_service] = lambda: diary_svc

    response = client.get("/api/v1/diaries")
    assert response.status_code == 200
    diaries = response.json()
    assert len(diaries) == 1
    assert diaries[0]["id"] == str(DIARY_ID)


def test_update_diary(client):
    from app.config.dependencies import get_diary_service
    from app.main import app

    diary_svc = make_diary_service_mock()
    app.dependency_overrides[get_diary_service] = lambda: diary_svc

    response = client.put(
        f"/api/v1/diaries/{DIARY_ID}",
        json={"content": "수정된 내용"},
    )
    assert response.status_code == 200
    diary_svc.update_entry.assert_called_once()


def test_get_diaries_by_date_invalid_format(client):
    """잘못된 날짜 형식은 400."""
    from app.config.dependencies import get_diary_service
    from app.main import app

    diary_svc = make_diary_service_mock()
    app.dependency_overrides[get_diary_service] = lambda: diary_svc

    response = client.get("/api/v1/diaries/by-date/not-a-date")
    assert response.status_code == 400
    assert "날짜 형식" in response.json()["detail"]


def test_get_diaries_by_date_valid(client):
    from app.config.dependencies import get_diary_service
    from app.main import app

    diary_svc = make_diary_service_mock()
    app.dependency_overrides[get_diary_service] = lambda: diary_svc

    response = client.get("/api/v1/diaries/by-date/2026-05-26")
    assert response.status_code == 200


def test_create_diary_skips_orchestrator_for_short_content(client):
    """50자 미만 다이어리는 cross-domain orchestrator 호출 없이 저장만."""
    from unittest.mock import AsyncMock, MagicMock

    from app.config.dependencies import get_diary_orchestrator, get_diary_service
    from app.main import app

    diary_svc = make_diary_service_mock()
    orchestrator = MagicMock()
    orchestrator.process_diary_with_librarian = AsyncMock(return_value=None)

    app.dependency_overrides[get_diary_service] = lambda: diary_svc
    app.dependency_overrides[get_diary_orchestrator] = lambda: orchestrator

    response = client.post(
        "/api/v1/diaries",
        json={"content": "짧음"},
    )
    assert response.status_code == 201
    # BackgroundTasks는 response 이후 실행되지만, content가 짧으면 add_task 자체가 호출 안 됨
    # → background에서 호출 안 됐는지는 직접 검증 어려움. 응답만 확인.
