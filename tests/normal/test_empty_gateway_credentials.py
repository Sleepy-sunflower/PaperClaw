"""Scenario: Gateway credentials are empty"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_empty_gateway_credentials_still_serve_health(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """对话凭证和嵌入凭证为空时，应用仍接受请求，/health 返回 HTTP 200。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@db:5432/paperclaw",
    )
    for name in (
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_MODEL",
    ):
        monkeypatch.setenv(name, "")
    monkeypatch.setattr("app.services.health.database_is_up", lambda database_url: True)
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "up"
