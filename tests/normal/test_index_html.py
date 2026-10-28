"""Scenario: Open the root page"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_root_page_is_html_with_entries(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """GET / 返回 HTTP 200 的 HTML，并包含产品名和两个入口。"""
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@127.0.0.1:1/paperclaw",
    )
    monkeypatch.setenv("FRONTEND_DIST", str(frontend))
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "文献引路" in response.text
    assert "文献库" in response.text
    assert "阅读助手" in response.text
