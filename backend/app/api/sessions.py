"""登录与当前会话。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.responses import json_error, json_ok
from app.db.users import (
    delete_session_by_token_hash,
    find_user,
    find_username_by_token_hash,
    insert_session,
)
from app.services.passwords import (
    burn_password_check,
    hash_token,
    new_token,
    password_matches,
)

router = APIRouter()


def _unauthenticated(request_id: str) -> JSONResponse:
    """用户名或密码不正确，或令牌无效。"""
    return json_error("unauthenticated", "未登录", request_id, 401)


@router.post("/api/v1/sessions", response_model=None)
async def login(request: Request) -> JSONResponse:
    """核对用户名和密码，成功时返回只展示一次的令牌。"""
    request_id = request.state.request_id
    try:
        body = await request.json()
    except Exception:
        return _unauthenticated(request_id)
    if not isinstance(body, dict):
        return _unauthenticated(request_id)
    username = body.get("username")
    password = body.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return _unauthenticated(request_id)
    user = find_user(request.app.state.database_url, username)
    if user is None:
        burn_password_check(password)
        return _unauthenticated(request_id)
    if not password_matches(password, user["password_hash"]):
        return _unauthenticated(request_id)
    token = new_token()
    insert_session(request.app.state.database_url, username, hash_token(token))
    return json_ok({"token": token, "username": username}, request_id)


@router.get("/api/v1/sessions/current", response_model=None)
def current_session(request: Request) -> JSONResponse:
    """用 Bearer 令牌读取当前用户名。"""
    request_id = request.state.request_id
    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix) or header == prefix:
        return _unauthenticated(request_id)
    username = find_username_by_token_hash(
        request.app.state.database_url,
        hash_token(header[len(prefix) :]),
    )
    if username is None:
        return _unauthenticated(request_id)
    return json_ok({"username": username}, request_id)


@router.delete("/api/v1/sessions/current", response_model=None)
def logout(request: Request) -> JSONResponse:
    """删除当前令牌对应的会话。"""
    request_id = request.state.request_id
    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix) or header == prefix:
        return _unauthenticated(request_id)
    deleted = delete_session_by_token_hash(
        request.app.state.database_url,
        hash_token(header[len(prefix) :]),
    )
    if not deleted:
        return _unauthenticated(request_id)
    return json_ok(None, request_id)
