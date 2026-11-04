"""登出的失败场景。"""

from __future__ import annotations

import psycopg
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app


def _client(monkeypatch, database_url: str) -> TestClient:  # type: ignore[no-untyped-def]
    """指向已清空的测试库。"""
    migrate_up(database_url)
    with psycopg.connect(database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()
    monkeypatch.setenv("DATABASE_URL", database_url)
    return TestClient(create_app())


def test_logout_without_a_token(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Logout without a token"""
    client = _client(monkeypatch, test_database_url)
    response = client.delete("/api/v1/sessions/current")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
