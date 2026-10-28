"""读取启动所需的环境变量。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """应用启动后持有的配置。"""

    database_url: str


def load_settings() -> Settings:
    """读取配置。缺少数据库连接时在接受请求前退出。"""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.strip():
        print("missing required setting: DATABASE_URL", file=sys.stderr)
        raise SystemExit(1)
    return Settings(database_url=database_url)
