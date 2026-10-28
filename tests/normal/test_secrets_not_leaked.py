"""Scenario: Response does not leak secrets"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_omits_secrets_after_startup(monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    """成功启动后，/health 的响应体和日志都不包含数据库口令或网关密钥。"""
    password = "db-password-value"
    gateway_key = "gateway-key-value"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql://paperclaw:{password}@db:5432/paperclaw",
    )
    monkeypatch.setenv("LLM_API_KEY", gateway_key)
    monkeypatch.setenv("EMBEDDING_API_KEY", gateway_key)
    monkeypatch.setattr("app.services.health.database_is_up", lambda database_url: True)
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert password not in response.text
    assert gateway_key not in response.text
    for line in capsys.readouterr().out.splitlines():
        if not line.startswith("{"):
            continue
        parsed = json.dumps(json.loads(line))
        assert password not in parsed
        assert gateway_key not in parsed
