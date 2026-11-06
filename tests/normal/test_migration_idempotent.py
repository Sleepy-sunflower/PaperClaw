"""已应用的迁移不再执行。"""

from __future__ import annotations

import uuid

import psycopg

from app.db.migrate import migrate_up


def test_applied_migrations_are_not_reapplied(test_database_url: str) -> None:
    """Scenario: Restart does not re-run applied migrations"""
    migrate_up(test_database_url)
    username = f"sentinel-{uuid.uuid4().hex[:8]}"
    try:
        with psycopg.connect(test_database_url) as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, "sentinel-not-a-real-hash"),
            )
            connection.commit()
            before = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]

        migrate_up(test_database_url)

        with psycopg.connect(test_database_url) as connection:
            sentinel = connection.execute(
                "SELECT 1 FROM users WHERE username = %s", (username,)
            ).fetchone()
            after = [
                row[0]
                for row in connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )
            ]
        assert sentinel is not None
        assert after == before
        assert len(set(after)) == len(after)
    finally:
        with psycopg.connect(test_database_url) as connection:
            connection.execute("DELETE FROM users WHERE username = %s", (username,))
            connection.commit()
