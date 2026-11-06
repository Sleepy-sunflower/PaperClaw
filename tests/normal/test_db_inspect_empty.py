"""空库时每一节都给出可读的空状态。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import db_inspect  # noqa: E402


def test_empty_database_reports_empty_sections(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Scenario: Empty database"""

    def fake_run_sql(command: list[str], sql: str) -> tuple[bool, str, str]:
        if sql.strip() == "SELECT 1":
            return True, "1\n", ""
        return True, "", ""

    monkeypatch.setattr(db_inspect, "run_sql", fake_run_sql)
    report, exit_code = db_inspect.build_report(["docker", "compose"], "", "")

    assert exit_code == 0
    for title in ("用户", "会话", "文献", "入库任务", "片段"):
        assert f"{title}（共 0 " in report
    for empty in (
        "还没有用户。",
        "还没有会话。",
        "还没有文献。",
        "还没有入库任务。",
        "还没有片段。",
    ):
        assert empty in report
    assert "Traceback" not in report
    assert "读不到这一节" not in report
