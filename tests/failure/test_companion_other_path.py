"""Scenario: Companion has no other route"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.companion_loader import load_companion_app


def test_companion_other_path_is_404() -> None:
    """除 /health 以外的路径返回 HTTP 404。"""
    client = TestClient(load_companion_app())
    response = client.get("/api/v1/papers")
    assert response.status_code == 404
