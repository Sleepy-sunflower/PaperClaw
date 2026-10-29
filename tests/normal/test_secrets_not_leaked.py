"""Scenario: Response does not leak secrets"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import create_app


def _log_text(capsys) -> str:  # type: ignore[no-untyped-def]
    """收集这次请求写出的 JSON 日志。"""
    lines = []
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("{"):
            lines.append(json.dumps(json.loads(line)))
    return "\n".join(lines)


def test_successful_health_omits_password(monkeypatch, capsys, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """真实连上数据库后，响应体和日志都不包含连接串里的口令或网关密钥。"""
    password = test_database_url.split(":", 2)[2].split("@", 1)[0]
    gateway_key = "gateway-key-value"
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("LLM_API_KEY", gateway_key)
    monkeypatch.setenv("EMBEDDING_API_KEY", gateway_key)
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert password not in response.text
    assert gateway_key not in response.text
    logged = _log_text(capsys)
    assert password not in logged
    assert gateway_key not in logged


def test_rejected_connection_omits_password(monkeypatch, capsys, test_database_url: str) -> None:  # type: ignore[no-untyped-def]
    """口令错误导致驱动报错时，口令也不进入响应体或日志。"""
    password = "rejected-db-password"
    user_and_host = test_database_url.split("://", 1)[1]
    user = user_and_host.split(":", 1)[0]
    host_and_db = user_and_host.split("@", 1)[1]
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql://{user}:{password}@{host_and_db}",
    )
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 503
    assert password not in response.text
    assert password not in _log_text(capsys)
