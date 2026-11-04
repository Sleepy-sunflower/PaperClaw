"""注册和登录的失败场景。"""

from __future__ import annotations

import psycopg
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app

_PASSWORD = "password1"


def _client(monkeypatch, database_url: str) -> TestClient:  # type: ignore[no-untyped-def]
    """指向已迁移的测试库。"""
    migrate_up(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()
    monkeypatch.setenv("DATABASE_URL", database_url)
    return TestClient(create_app())


def _without_request_id(body: dict[str, object]) -> dict[str, object]:
    """去掉每次都会变的请求标识。"""
    copied = dict(body)
    copied.pop("request_id", None)
    return copied


def test_reject_invalid_registration(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Reject invalid registration"""
    client = _client(monkeypatch, test_database_url)
    empty_name = client.post(
        "/api/v1/users",
        json={"username": "", "password": _PASSWORD},
    )
    uppercase = client.post(
        "/api/v1/users",
        json={"username": "Reader", "password": _PASSWORD},
    )
    short_password = client.post(
        "/api/v1/users",
        json={"username": "reader-one", "password": ""},
    )
    assert empty_name.status_code == 400
    assert empty_name.json()["code"] == "invalid_argument"
    assert uppercase.status_code == 400
    assert short_password.status_code == 400
    with psycopg.connect(test_database_url) as connection:
        count = connection.execute("SELECT count(*) FROM users").fetchone()
    assert count is not None
    assert count[0] == 0


def test_reject_duplicate_username(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Reject duplicate username"""
    client = _client(monkeypatch, test_database_url)
    client.post("/api/v1/users", json={"username": "reader-one", "password": _PASSWORD})
    response = client.post(
        "/api/v1/users",
        json={"username": "reader-one", "password": "password2"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "already_exists"
    with psycopg.connect(test_database_url) as connection:
        count = connection.execute("SELECT count(*) FROM users").fetchone()
    assert count is not None
    assert count[0] == 1


def test_wrong_password_matches_unknown_user(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Wrong password matches unknown user"""
    client = _client(monkeypatch, test_database_url)
    client.post("/api/v1/users", json={"username": "reader-one", "password": _PASSWORD})
    wrong = client.post(
        "/api/v1/sessions",
        json={"username": "reader-one", "password": "wrong-password"},
    )
    missing = client.post(
        "/api/v1/sessions",
        json={"username": "nobody", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.json()["code"] == "unauthenticated"
    assert _without_request_id(wrong.json()) == _without_request_id(missing.json())


def test_reject_missing_or_invalid_token(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Reject missing or invalid token"""
    client = _client(monkeypatch, test_database_url)
    missing = client.get("/api/v1/sessions/current")
    invalid = client.get(
        "/api/v1/sessions/current",
        headers={"Authorization": "Bearer not-a-token"},
    )
    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json()["code"] == "unauthenticated"
    assert "username" not in missing.text
    assert "username" not in invalid.text
    assert _without_request_id(missing.json()) == _without_request_id(invalid.json())
