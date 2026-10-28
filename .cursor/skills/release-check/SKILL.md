---
name: release-check
description: 按 README 启动文献引路并检查 /health。在用户要求发布、打标签或确认本机可运行时使用。
---

# 按规范发一次版本

1. 运行 `pytest`，退出码必须为 0。
2. 按 `README.md` 复制 `.env.example` 并执行 `docker compose up --build`。
3. 请求 `http://localhost:8000/health`，确认 HTTP 200，且数据库为连通。
4. 任一步失败就停止，不要打标签。修好后从第 1 步重做。
