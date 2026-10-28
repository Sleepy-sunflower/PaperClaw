"""组装应用、请求日志和静态页面。"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.health import router as health_router
from app.config import load_settings


class RequestLogMiddleware(BaseHTTPMiddleware):
    """为每个请求生成标识，并在结束时写一行 JSON 日志。"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """写入请求标识、调用后续处理，并输出一行日志。"""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        line = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": "info",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
        }
        print(json.dumps(line), flush=True)
        return response


def create_app() -> FastAPI:
    """创建应用。缺少数据库连接时在监听端口之前退出。"""
    settings = load_settings()
    app = FastAPI()
    app.state.database_url = settings.database_url
    app.add_middleware(RequestLogMiddleware)
    app.include_router(health_router)

    @app.api_route(
        "/api/{full_path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    def unknown_api(full_path: str, request: Request) -> JSONResponse:
        """未定义的业务路径返回 404，并带上本次请求标识。"""
        del full_path
        return JSONResponse(
            status_code=404,
            content={
                "code": "not_found",
                "message": "not found",
                "data": None,
                "request_id": request.state.request_id,
            },
        )

    dist = Path(os.environ.get("FRONTEND_DIST", "frontend/dist"))
    index = dist / "index.html"
    assets = dist / "assets"
    if assets.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", response_model=None)
    @app.get("/{full_path:path}", response_model=None)
    def frontend(full_path: str = "") -> FileResponse | JSONResponse:
        """在健康检查和业务接口之后，把其余 GET 交给前端页面。"""
        del full_path
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            status_code=404,
            content={"code": "not_found", "message": "not found", "data": None},
        )

    return app
