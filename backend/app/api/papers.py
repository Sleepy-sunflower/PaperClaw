"""文献上传、列表、读取和任务状态接口。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.responses import json_error, json_ok
from app.services.accounts import user_id_for_token
from app.services.papers import (
    accept_upload,
    list_ready_papers,
    read_paper,
    read_task,
)

router = APIRouter()


def _unauthenticated(request_id: str) -> JSONResponse:
    """没有令牌或令牌无效。"""
    return json_error("unauthenticated", "未登录", request_id, 401)


def _not_found(request_id: str) -> JSONResponse:
    """他人的资源与不存在的资源使用同一个响应。"""
    return json_error("not_found", "not found", request_id, 404)


def _invalid(request_id: str) -> JSONResponse:
    """上传内容或标识不符合要求。"""
    return json_error("invalid_argument", "请求不符合要求", request_id, 400)


def _bearer_token(request: Request) -> str | None:
    """取出 Bearer 令牌。没有或为空时返回 None。"""
    header = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not header.startswith(prefix) or header == prefix:
        return None
    return header[len(prefix) :]


def _user_id(request: Request) -> str | None:
    """用令牌取出当前用户标识。无效时返回 None。"""
    token = _bearer_token(request)
    if token is None:
        return None
    return user_id_for_token(request.app.state.database_url, token)


@router.post("/api/v1/papers", response_model=None)
async def upload_paper(request: Request) -> JSONResponse:
    """留下 PDF 并放入任务，马上返回，不调用嵌入接口。"""
    request_id = request.state.request_id
    user_id = _user_id(request)
    if user_id is None:
        return _unauthenticated(request_id)
    try:
        form = await request.form()
        upload = form.get("file")
        filename = str(getattr(upload, "filename", "") or "")
        content = await upload.read()  # type: ignore[union-attr]
    except Exception:
        return _invalid(request_id)
    outcome = accept_upload(request.app.state.database_url, user_id, filename, content)
    if outcome[0] == "invalid":
        return _invalid(request_id)
    _, task_id, status = outcome
    return json_ok({"task_id": task_id, "status": status}, request_id, 202)


@router.get("/api/v1/papers", response_model=None)
def list_papers_endpoint(request: Request) -> JSONResponse:
    """只列出当前用户已可检索的文献标识和文件名。"""
    request_id = request.state.request_id
    user_id = _user_id(request)
    if user_id is None:
        return _unauthenticated(request_id)
    return json_ok(list_ready_papers(request.app.state.database_url, user_id), request_id)


@router.get("/api/v1/papers/{paper_id}", response_model=None)
def read_paper_endpoint(paper_id: str, request: Request) -> JSONResponse:
    """读取当前用户的一份文献。"""
    request_id = request.state.request_id
    user_id = _user_id(request)
    if user_id is None:
        return _unauthenticated(request_id)
    kind, *rest = read_paper(request.app.state.database_url, user_id, paper_id)
    if kind == "invalid":
        return _invalid(request_id)
    if kind == "missing":
        return _not_found(request_id)
    return json_ok(rest[0], request_id)


@router.get("/api/v1/paper-tasks/{task_id}", response_model=None)
def read_task_endpoint(task_id: str, request: Request) -> JSONResponse:
    """读取当前用户的一条任务状态。"""
    request_id = request.state.request_id
    user_id = _user_id(request)
    if user_id is None:
        return _unauthenticated(request_id)
    kind, *rest = read_task(request.app.state.database_url, user_id, task_id)
    if kind == "invalid":
        return _invalid(request_id)
    if kind == "missing":
        return _not_found(request_id)
    return json_ok(rest[0], request_id)
