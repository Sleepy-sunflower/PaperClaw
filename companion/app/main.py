"""伴随进程。不读取数据库配置，也不连接数据库。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


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
    """创建只含存活检查的应用。"""
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/health")
    def read_health(request: Request) -> JSONResponse:
        """报告伴随进程已启动。"""
        return JSONResponse(
            status_code=200,
            content={
                "service": "companion",
                "status": "up",
                "request_id": request.state.request_id,
            },
        )

    return app
