"""栈没有启动时，脚本以非 0 退出并写明下一步。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import db_inspect  # noqa: E402

_ERROR = 'service "db" is not running'


def test_stopped_stack_is_reported_readably(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Stack is stopped"""
    monkeypatch.setattr(
        db_inspect,
        "run_sql",
        lambda command, sql: (False, "", _ERROR),
    )
    report, exit_code = db_inspect.build_report(["docker", "compose"], "", "")

    assert exit_code == 1
    assert "请先运行 docker compose up -d" in report
    assert _ERROR in report
    assert "Traceback" not in report


def test_stopped_stack_exits_non_zero_without_writing(
    monkeypatch, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    """Scenario: Stack is stopped"""
    output = tmp_path / "db-inspect.txt"
    monkeypatch.setattr(
        db_inspect,
        "run_sql",
        lambda command, sql: (False, "", _ERROR),
    )
    monkeypatch.setattr(
        sys, "argv", ["db_inspect.py", "--output", str(output)]
    )

    assert db_inspect.main() == 1
    assert not output.exists()
