"""组合应用与数据库的健康检查结果。"""

from __future__ import annotations

from app.db.ping import database_is_up


def build_health(database_url: str, request_id: str) -> tuple[int, dict[str, object]]:
    """返回健康检查的 HTTP 状态和响应体。"""
    if database_is_up(database_url):
        return 200, {
            "status": "ok",
            "checks": {"app": "up", "database": "up"},
            "request_id": request_id,
        }
    return 503, {
        "status": "degraded",
        "checks": {"app": "up", "database": "down"},
        "request_id": request_id,
    }
