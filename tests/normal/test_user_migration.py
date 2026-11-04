"""迁移建表后再回滚，vector 扩展还在。"""

from __future__ import annotations

import psycopg

from app.db.migrate import migrate_down, migrate_up


def test_users_sessions_migration_rolls_back(test_database_url: str) -> None:
    """执行迁移再回滚后，users 和 sessions 消失，vector 扩展仍在。"""
    with psycopg.connect(test_database_url) as connection:
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.commit()
    migrate_up(test_database_url)
    migrate_down(test_database_url)
    with psycopg.connect(test_database_url) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('users', 'sessions')
                """
            ).fetchall()
        }
        extension = connection.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
    assert tables == set()
    assert extension is not None
    migrate_up(test_database_url)
