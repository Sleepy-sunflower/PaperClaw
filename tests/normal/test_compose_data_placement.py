"""Compose 编排把数据库数据放在卷里，不对宿主机发布端口。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATHS = ("pgdata", "data", "db/data")


def _compose_config() -> dict[str, object]:
    """读出 Compose 解析后的编排，用 JSON 格式避免依赖 YAML 库。"""
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return json.loads(result.stdout)


def _db_service() -> dict[str, object]:
    services = _compose_config()["services"]
    assert isinstance(services, dict)
    db = services["db"]
    assert isinstance(db, dict)
    return db


def test_database_data_lives_in_a_named_volume() -> None:
    """Scenario: git status stays clean"""
    volumes = _db_service().get("volumes")
    assert isinstance(volumes, list)
    named = [
        entry
        for entry in volumes
        if isinstance(entry, dict)
        and entry.get("type") == "volume"
        and entry.get("target") == "/var/lib/postgresql/data"
    ]
    assert named, f"db 的数据目录没有挂在命名卷上：{volumes}"

    for relative in DATA_PATHS:
        assert not (ROOT / relative).exists(), f"仓库工作区里出现了数据目录 {relative}"

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout
    listed = [line[3:].strip().strip('"') for line in status.splitlines() if line]
    for path in listed:
        for relative in DATA_PATHS:
            assert path != relative and not path.startswith(relative + "/"), (
                f"git status 里出现了数据路径：{path}"
            )


def test_database_port_is_not_published() -> None:
    """Scenario: Database port is not reachable from the host"""
    assert not _db_service().get("ports")
