"""执行数据库迁移。只记录已经应用的版本。"""

from __future__ import annotations

from pathlib import Path

import psycopg

_MIGRATIONS = Path(__file__).parent / "migrations"
_VERSIONS = ("001_users_sessions", "002_papers_chunks")


def _ensure_table(connection: psycopg.Connection) -> None:
    """建立记录已应用版本的表。"""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version text PRIMARY KEY
        )
        """
    )


def migrate_up(database_url: str) -> None:
    """按顺序应用还没有执行的迁移。重复执行不会再改表。"""
    with psycopg.connect(database_url) as connection:
        _ensure_table(connection)
        for version in _VERSIONS:
            applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (version,),
            ).fetchone()
            if applied is not None:
                continue
            connection.execute(
                (_MIGRATIONS / f"{version}.up.sql").read_text(encoding="utf-8")
            )
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (version,),
            )
        connection.commit()


def migrate_down(database_url: str, version: str | None = None) -> None:
    """回滚迁移。给出 version 时只撤回这一份，否则按相反顺序撤回全部。"""
    with psycopg.connect(database_url) as connection:
        _ensure_table(connection)
        targets = (
            [v for v in reversed(_VERSIONS) if v == version]
            if version is not None
            else list(reversed(_VERSIONS))
        )
        for target in targets:
            applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = %s",
                (target,),
            ).fetchone()
            if applied is None:
                continue
            connection.execute(
                (_MIGRATIONS / f"{target}.down.sql").read_text(encoding="utf-8")
            )
            connection.execute(
                "DELETE FROM schema_migrations WHERE version = %s",
                (target,),
            )
        connection.commit()


if __name__ == "__main__":
    from app.config import load_settings

    migrate_up(load_settings().database_url)
