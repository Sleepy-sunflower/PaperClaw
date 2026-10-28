"""检查数据库是否接受查询。"""

from __future__ import annotations

import psycopg


def database_is_up(database_url: str) -> bool:
    """在 2 秒内执行 SELECT 1。连不上或查询失败时返回 False。"""
    try:
        with psycopg.connect(database_url, connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception:
        return False
    return True
