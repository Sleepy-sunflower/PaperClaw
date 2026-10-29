"""为需要真实连接的用例启动一个独立的测试数据库。"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator

import psycopg
import pytest

_CONTAINER = "paperclaw-pytest-pg"
_PORT = "54329"
_PASSWORD = "pytest-only-password"
_URL = f"postgresql://paperclaw:{_PASSWORD}@127.0.0.1:{_PORT}/paperclaw_test"


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """启动 paperclaw_test，与 Compose 里的应用库不是同一个。"""
    subprocess.run(["docker", "rm", "-f", _CONTAINER], check=False, capture_output=True)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            _CONTAINER,
            "-e",
            "POSTGRES_USER=paperclaw",
            "-e",
            f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e",
            "POSTGRES_DB=paperclaw_test",
            "-p",
            f"{_PORT}:5432",
            "pgvector/pgvector:pg16",
        ],
        check=True,
    )
    ready = False
    for _ in range(30):
        try:
            with psycopg.connect(_URL, connect_timeout=2) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            ready = True
            break
        except Exception:
            time.sleep(1)
    if not ready:
        subprocess.run(["docker", "rm", "-f", _CONTAINER], check=False, capture_output=True)
        raise RuntimeError("测试数据库没有在 30 秒内就绪")
    yield _URL
    subprocess.run(["docker", "rm", "-f", _CONTAINER], check=False, capture_output=True)
