"""Scenario: Companion health"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.companion_loader import load_companion_app


def test_companion_health() -> None:
    """GET /health 返回 200，并把进程标为 companion。"""
    client = TestClient(load_companion_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "companion"
    assert body["status"] == "up"
    assert body["request_id"] == response.headers["X-Request-Id"]
