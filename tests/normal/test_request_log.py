"""Scenario: Health request is logged"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_writes_one_json_line(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    """一次 /health 产生一行日志，请求标识与响应头相同。"""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@127.0.0.1:1/paperclaw",
    )
    client = TestClient(create_app())
    response = client.get("/health")
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.startswith("{")]
    assert len(lines) == 1
    log = json.loads(lines[0])
    assert log["request_id"] == response.headers["X-Request-Id"]
    assert log["method"] == "GET"
    assert log["path"] == "/health"
    assert log["status"] == response.status_code
    assert set(log) >= {"time", "level", "request_id", "method", "path", "status"}
