"""注册、登录和当前会话的接口场景。"""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app

_PASSWORD = "password1"


@pytest.fixture
def client(monkeypatch, test_database_url: str):  # type: ignore[no-untyped-def]
    """每个用例使用已迁移的独立测试库，并在结束后清空用户。"""
    migrate_up(test_database_url)
    with psycopg.connect(test_database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    yield TestClient(create_app())
    with psycopg.connect(test_database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()


def _without_request_id(body: dict[str, object]) -> dict[str, object]:
    """去掉每次都会变的请求标识。"""
    copied = dict(body)
    copied.pop("request_id", None)
    return copied


def test_register_a_new_user(client: TestClient) -> None:
    """Scenario: Register a new user"""
    response = client.post(
        "/api/v1/users",
        json={"username": "reader-one", "password": _PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "ok"
    assert body["data"] == {"username": "reader-one"}
    assert "password" not in response.text
    assert _PASSWORD not in response.text


def test_login_succeeds(client: TestClient) -> None:
    """Scenario: Login succeeds"""
    client.post("/api/v1/users", json={"username": "reader-one", "password": _PASSWORD})
    response = client.post(
        "/api/v1/sessions",
        json={"username": "reader-one", "password": _PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "reader-one"
    assert isinstance(data["token"], str) and data["token"]
    assert _PASSWORD not in response.text


def test_read_current_user(client: TestClient) -> None:
    """Scenario: Read current user"""
    client.post("/api/v1/users", json={"username": "reader-one", "password": _PASSWORD})
    token = client.post(
        "/api/v1/sessions",
        json={"username": "reader-one", "password": _PASSWORD},
    ).json()["data"]["token"]
    response = client.get(
        "/api/v1/sessions/current",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "reader-one"
