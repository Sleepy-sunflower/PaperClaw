"""Scenario: Request without credentials"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.ping import database_is_up
from app.main import create_app


def test_health_without_credentials(monkeypatch, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """不带 Authorization，并且数据库真的接受 SELECT 1 时，/health 报告两边都已启动。"""
    assert database_is_up(test_database_url) is True
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    client = TestClient(create_app())
    response = client.get("/health")
    assert "authorization" not in {name.lower() for name in response.request.headers}
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"app": "up", "database": "up"}
    assert body["request_id"] == response.headers["X-Request-Id"]
