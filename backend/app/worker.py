"""处理进程：领取任务，抽字、切块、嵌入并写入。"""

from __future__ import annotations

import time

from app.config import load_settings
from app.db.migrate import migrate_up
from app.services.papers import process_next_task


def main() -> None:
    """循环领取待处理的任务，直到进程被停掉。"""
    settings = load_settings()
    migrate_up(settings.database_url)
    while True:
        if not process_next_task(settings.database_url):
            time.sleep(1)


if __name__ == "__main__":
    main()
