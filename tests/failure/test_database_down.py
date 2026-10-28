"""Scenario: Database is stopped"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_unreachable_database_reports_down(monkeypatch: object) -> None:
    """无法连接的 DATABASE_URL 使 /health 返回 HTTP 503，且数据库为 down。"""
    monkeypatch.setenv(  # type: ignore[attr-defined]
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@127.0.0.1:1/paperclaw",
    )
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["checks"]["app"] == "up"
    assert body["checks"]["database"] == "down"
    assert body["request_id"]
