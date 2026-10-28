"""按文件加载伴随进程，避免与应用包同名。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import FastAPI


def load_companion_app() -> FastAPI:
    """加载 companion/app/main.py 并创建应用。"""
    path = Path(__file__).resolve().parents[1] / "companion" / "app" / "main.py"
    spec = importlib.util.spec_from_file_location("companion_main", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_app()
