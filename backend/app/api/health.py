"""健康检查接口。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.health import build_health

router = APIRouter()


@router.get("/health")
def read_health(request: Request) -> JSONResponse:
    """不要求登录，报告应用与数据库是否连通。"""
    status_code, body = build_health(
        request.app.state.database_url,
        request.state.request_id,
    )
    return JSONResponse(status_code=status_code, content=body)
