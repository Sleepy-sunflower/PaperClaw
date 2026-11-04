"""口令哈希与令牌哈希。"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()
_dummy_hash = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    """返回口令的 Argon2 哈希。"""
    return _hasher.hash(password)


def password_matches(password: str, password_hash: str) -> bool:
    """核对口令。不匹配时返回 False。"""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def burn_password_check(password: str) -> None:
    """用户不存在时仍做一次哈希核对，避免用耗时区分用户是否存在。"""
    password_matches(password, _dummy_hash)


def new_token() -> str:
    """生成只向客户端展示一次的令牌。"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """返回令牌的 SHA-256 十六进制摘要。"""
    return hashlib.sha256(token.encode()).hexdigest()
