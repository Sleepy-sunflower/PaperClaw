"""注册与会话的业务。"""

from __future__ import annotations

from typing import Literal

from psycopg.errors import UniqueViolation

from app.db.users import (
    delete_session_by_token_hash,
    find_user,
    find_user_id_by_token_hash,
    find_username_by_token_hash,
    insert_session,
    insert_user,
)
from app.services.passwords import (
    burn_password_check,
    hash_password,
    hash_token,
    new_token,
    password_matches,
)

RegisterResult = Literal["created", "exists"]


def register_account(database_url: str, username: str, password: str) -> RegisterResult:
    """创建用户。用户名已存在时返回 exists。"""
    try:
        insert_user(database_url, username, hash_password(password))
    except UniqueViolation:
        return "exists"
    return "created"


def open_session(database_url: str, username: str, password: str) -> str | None:
    """核对口令并写入会话。成功时返回只展示一次的令牌。"""
    user = find_user(database_url, username)
    if user is None:
        burn_password_check(password)
        return None
    if not password_matches(password, user["password_hash"]):
        return None
    token = new_token()
    insert_session(database_url, username, hash_token(token))
    return token


def username_for_token(database_url: str, token: str) -> str | None:
    """用令牌读取当前用户名。无效时返回 None。"""
    return find_username_by_token_hash(database_url, hash_token(token))


def user_id_for_token(database_url: str, token: str) -> str | None:
    """用令牌读取当前用户标识。无效时返回 None。"""
    return find_user_id_by_token_hash(database_url, hash_token(token))


def close_session(database_url: str, token: str) -> bool:
    """删除这枚令牌对应的会话。删到时返回 True。"""
    return delete_session_by_token_hash(database_url, hash_token(token))
