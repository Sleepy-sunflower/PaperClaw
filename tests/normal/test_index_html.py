"""Scenario: Open the root page"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_built_root_page_contains_entries(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """构建产物里的首页是 HTTP 200 的 HTML，并包含产品名和两个入口。"""
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    npm = shutil.which("npm")
    assert npm is not None
    built = subprocess.run(
        [npm, "run", "build"],
        cwd=frontend,
        capture_output=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr.decode("utf-8", errors="replace")
    dist = frontend / "dist"
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://paperclaw:paperclaw@127.0.0.1:1/paperclaw",
    )
    monkeypatch.setenv("FRONTEND_DIST", str(dist))
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/src/main.tsx" not in response.text
    assert "文献引路" in response.text
    assert "文献库" in response.text
    assert "阅读助手" in response.text
