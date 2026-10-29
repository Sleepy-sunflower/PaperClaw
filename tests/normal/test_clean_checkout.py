"""Scenario: Start from a clean checkout"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def test_readme_startup_health_reports_database_up() -> None:
    """执行 README 的启动命令后，GET /health 返回 HTTP 200，且数据库为 up。"""
    root = Path(__file__).resolve().parents[2]
    started = subprocess.run(
        ["docker", "compose", "up", "--build", "-d"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert started.returncode == 0, started.stderr.decode("utf-8", errors="replace")
    body: dict[str, object] = {}
    status = 0
    last_error = ""
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://localhost:8000/health") as response:
                status = response.status
                body = json.loads(response.read().decode())
            if status == 200 and body.get("checks", {}).get("database") == "up":
                break
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            last_error = str(error)
        time.sleep(2)
    assert status == 200, last_error
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "up"
