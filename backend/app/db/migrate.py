"""执行数据库迁移。只记录已经应用的版本。"""

from __future__ import annotations

from pathlib import Path

import psycopg

_MIGRATIONS = Path(__file__).parent / "migrations"
_VERSION = "001_users_sessions"


def migrate_up(database_url: str) -> None:
    """建 users 和 sessions。重复执行不会再改表。"""
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version text PRIMARY KEY
            )
            """
        )
        applied = connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = %s",
            (_VERSION,),
        ).fetchone()
        if applied is not None:
            return
        connection.execute((_MIGRATIONS / f"{_VERSION}.up.sql").read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)",
            (_VERSION,),
        )
        connection.commit()


def migrate_down(database_url: str) -> None:
    """先删 sessions，再删 users。"""
    with psycopg.connect(database_url) as connection:
        connection.execute((_MIGRATIONS / f"{_VERSION}.down.sql").read_text(encoding="utf-8"))
        connection.execute(
            "DELETE FROM schema_migrations WHERE version = %s",
            (_VERSION,),
        )
        connection.commit()
