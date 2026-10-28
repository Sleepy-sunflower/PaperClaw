"""Scenario: Unknown path"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_unknown_api_path(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """GET /api/v1/missing 返回 404，响应体中的请求标识与响应头一致。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@127.0.0.1:1/paperclaw",
    )
    client = TestClient(create_app())
    response = client.get("/api/v1/missing")
    assert response.status_code == 404
    assert response.json()["request_id"] == response.headers["X-Request-Id"]
