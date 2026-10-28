"""Scenario: Start from a clean checkout"""

from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(
    os.environ.get("PAPERCLAW_LIVE") != "1",
    reason="需要已按 README 启动，并设置 PAPERCLAW_LIVE=1",
)
def test_running_stack_health_is_ok() -> None:
    """按 README 启动后，GET /health 返回 HTTP 200。"""
    import urllib.request

    with urllib.request.urlopen("http://localhost:8000/health") as response:
        assert response.status == 200
