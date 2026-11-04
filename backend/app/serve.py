"""启动前先执行迁移，再监听端口。"""

from __future__ import annotations

import uvicorn

from app.config import load_settings
from app.db.migrate import migrate_up
from app.main import create_app


def main() -> None:
    """缺少数据库连接时退出；否则建表并启动应用。"""
    settings = load_settings()
    migrate_up(settings.database_url)
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
