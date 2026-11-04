"""登出接口场景。"""

from __future__ import annotations

import psycopg
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app

_PASSWORD = "password1"


def _client(monkeypatch, database_url: str) -> TestClient:  # type: ignore[no-untyped-def]
    """指向已清空的测试库。"""
    migrate_up(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()
    monkeypatch.setenv("DATABASE_URL", database_url)
    return TestClient(create_app())


def test_logout_succeeds(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Logout succeeds"""
    client = _client(monkeypatch, test_database_url)
    client.post("/api/v1/users", json={"username": "reader-one", "password": _PASSWORD})
    token = client.post(
        "/api/v1/sessions",
        json={"username": "reader-one", "password": _PASSWORD},
    ).json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}
    deleted = client.delete("/api/v1/sessions/current", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["code"] == "ok"
    assert deleted.json()["data"] is None
    assert token not in deleted.text
    current = client.get("/api/v1/sessions/current", headers=headers)
    assert current.status_code == 401
    again = client.delete("/api/v1/sessions/current", headers=headers)
    assert again.status_code == 401
