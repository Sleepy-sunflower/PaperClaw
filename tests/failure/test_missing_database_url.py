"""Scenario: Database connection is absent"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_missing_database_url_exits() -> None:
    """DATABASE_URL 缺失时进程以非 0 退出，并写明所缺配置。"""
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["LLM_API_KEY"] = ""
    env["EMBEDDING_API_KEY"] = ""
    backend = Path(__file__).resolve().parents[2] / "backend"
    result = subprocess.run(
        [sys.executable, "-c", "from app.main import create_app; create_app()"],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "missing required setting: DATABASE_URL" in result.stderr
