"""注册接口。"""

from __future__ import annotations

import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from psycopg.errors import UniqueViolation

from app.api.responses import json_error, json_ok
from app.db.users import insert_user
from app.services.passwords import hash_password

router = APIRouter()
_USERNAME = re.compile(r"[a-z0-9-]{1,32}")


def _invalid(request_id: str) -> JSONResponse:
    """用户名或密码不符合规则。"""
    return json_error(
        "invalid_argument",
        "用户名或密码不符合要求",
        request_id,
        400,
    )


@router.post("/api/v1/users", response_model=None)
async def register_user(request: Request) -> JSONResponse:
    """创建用户。不要求令牌。"""
    request_id = request.state.request_id
    try:
        body = await request.json()
    except Exception:
        return _invalid(request_id)
    if not isinstance(body, dict):
        return _invalid(request_id)
    username = body.get("username")
    password = body.get("password")
    if not isinstance(username, str) or _USERNAME.fullmatch(username) is None:
        return _invalid(request_id)
    if not isinstance(password, str) or not 1 <= len(password) <= 72:
        return _invalid(request_id)
    try:
        insert_user(request.app.state.database_url, username, hash_password(password))
    except UniqueViolation:
        return json_error("already_exists", "用户名已被占用", request_id, 409)
    return json_ok({"username": username}, request_id, 201)
