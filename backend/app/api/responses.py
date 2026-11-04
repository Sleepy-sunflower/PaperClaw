"""统一业务响应。"""

from __future__ import annotations

from fastapi.responses import JSONResponse


def json_ok(data: object, request_id: str, status_code: int = 200) -> JSONResponse:
    """返回成功响应。"""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": "ok",
            "message": "",
            "data": data,
            "request_id": request_id,
        },
    )


def json_error(
    code: str,
    message: str,
    request_id: str,
    status_code: int,
) -> JSONResponse:
    """返回失败响应。"""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "data": None,
            "request_id": request_id,
        },
    )
