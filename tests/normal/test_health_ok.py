"""Scenario: Request without credentials"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_without_credentials(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """不带 Authorization 时，/health 报告应用与数据库均已启动。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@db:5432/paperclaw",
    )
    monkeypatch.setattr("app.services.health.database_is_up", lambda database_url: True)
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"app": "up", "database": "up"}
    assert body["request_id"] == response.headers["X-Request-Id"]
    assert "Authorization" not in response.request.headers
