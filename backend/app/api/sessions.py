"""登录与当前会话。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.responses import json_error, json_ok
from app.services.accounts import close_session, open_session, username_for_token

router = APIRouter()


def _unauthenticated(request_id: str) -> JSONResponse:
    """用户名或密码不正确，或令牌无效。"""
    return json_error("unauthenticated", "未登录", request_id, 401)


def _bearer_token(request: Request) -> str | None:
    """取出 Bearer 令牌。没有或为空时返回 None。"""
    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix) or header == prefix:
        return None
    return header[len(prefix) :]


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
    token = open_session(request.app.state.database_url, username, password)
    if token is None:
        return _unauthenticated(request_id)
    return json_ok({"token": token, "username": username}, request_id)


@router.get("/api/v1/sessions/current", response_model=None)
def current_session(request: Request) -> JSONResponse:
    """用 Bearer 令牌读取当前用户名。"""
    request_id = request.state.request_id
    token = _bearer_token(request)
    if token is None:
        return _unauthenticated(request_id)
    username = username_for_token(request.app.state.database_url, token)
    if username is None:
        return _unauthenticated(request_id)
    return json_ok({"username": username}, request_id)


@router.delete("/api/v1/sessions/current", response_model=None)
def logout(request: Request) -> JSONResponse:
    """删除当前令牌对应的会话。"""
    request_id = request.state.request_id
    token = _bearer_token(request)
    if token is None:
        return _unauthenticated(request_id)
    if not close_session(request.app.state.database_url, token):
        return _unauthenticated(request_id)
    return json_ok(None, request_id)
