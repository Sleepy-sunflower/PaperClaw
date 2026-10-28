"""Scenario: Database connection is absent

DATABASE_URL 允许值的两端：全空白视为缺失，最短的非空白字符串视为已填写。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _start(database_url: str) -> subprocess.CompletedProcess[str]:
    """用给定的数据库连接尝试创建应用。"""
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["LLM_API_KEY"] = ""
    env["EMBEDDING_API_KEY"] = ""
    backend = Path(__file__).resolve().parents[2] / "backend"
    return subprocess.run(
        [sys.executable, "-c", "from app.main import create_app; create_app()"],
        cwd=backend,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_blank_database_url_is_rejected() -> None:
    """全空白处于缺失一端，进程以非 0 退出并写明 DATABASE_URL。"""
    result = _start("   ")
    assert result.returncode != 0
    assert "missing required setting: DATABASE_URL" in result.stderr


def test_shortest_database_url_is_accepted() -> None:
    """单个非空白字符处于已填写一端，进程不因缺失配置退出。"""
    result = _start("x")
    assert result.returncode == 0
    assert "missing required setting" not in result.stderr
