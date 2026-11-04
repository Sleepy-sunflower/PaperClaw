"""用户与会话的数据库访问。"""

from __future__ import annotations

from typing import TypedDict

import psycopg


class UserRow(TypedDict):
    """users 表中登录需要的列。"""

    username: str
    password_hash: str


def insert_user(database_url: str, username: str, password_hash: str) -> None:
    """插入一个用户。用户名重复时抛出唯一约束错误。"""
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
            """,
            (username, password_hash),
        )
        connection.commit()


def find_user(database_url: str, username: str) -> UserRow | None:
    """按用户名取出用户。没有时返回 None。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT username, password_hash
            FROM users
            WHERE username = %s
            """,
            (username,),
        ).fetchone()
    if row is None:
        return None
    return {"username": row[0], "password_hash": row[1]}


def insert_session(database_url: str, username: str, token_hash: str) -> None:
    """为已有用户写入一条会话。"""
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO sessions (user_id, token_hash)
            SELECT id, %s FROM users WHERE username = %s
            """,
            (token_hash, username),
        )
        connection.commit()


def find_username_by_token_hash(database_url: str, token_hash: str) -> str | None:
    """按令牌哈希取出用户名。没有时返回 None。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT users.username
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = %s
            """,
            (token_hash,),
        ).fetchone()
    if row is None:
        return None
    return str(row[0])


def delete_session_by_token_hash(database_url: str, token_hash: str) -> bool:
    """按令牌哈希删除会话。删到一行时返回 True。"""
    with psycopg.connect(database_url) as connection:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE token_hash = %s",
            (token_hash,),
        )
        connection.commit()
        return cursor.rowcount == 1
