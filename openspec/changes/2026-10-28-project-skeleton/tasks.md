## 1. 配置样例

- [x] 1.1 添加 `.env.example`，只含键名、不含值：`DATABASE_URL`、`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`。核对文件中没有口令或密钥明文。
- [x] 1.2 在 `.gitignore` 中忽略本变更会产生的 `.venv/`、`__pycache__/`、`node_modules/` 和 `frontend/dist/`。用 `git check-ignore` 确认这四类路径会被忽略。

## 2. 应用进程

- [x] 2.1 按 `design.md` 建立 `backend/app` 的配置、路由、服务和数据访问模块。检查健康检查的调用链是 `api/health.py` → `services/health.py` → `db/ping.py`，路由文件中没有 SQL。
- [x] 2.2 实现启动检查：`DATABASE_URL` 缺失或空白时，在监听端口之前以非 0 退出，输出包含 `missing required setting: DATABASE_URL`。空的 `LLM_*` 和 `EMBEDDING_*` 不导致退出。用 pytest 覆盖这两个场景。
- [x] 2.3 实现 `GET /health`：无 `Authorization` 也可访问；数据库 `SELECT 1` 在 2 秒内成功时返回 HTTP 200，体为 `status=ok`、`checks.app=up`、`checks.database=up`，并含 `request_id`；连接失败时进程继续运行，返回 HTTP 503，`database` 为 `down`。响应体不含口令或网关密钥。用无法连接的 `DATABASE_URL` 做 pytest，不启动 Compose。
- [x] 2.4 为每个请求生成 `X-Request-Id`，并在 stdout 写一行 JSON，字段为 `time`、`level`、`request_id`、`method`、`path`、`status`。`GET /api/v1/missing` 返回 HTTP 404 JSON，且 `request_id` 与响应头一致。用 pytest 截获日志并断言只有一行、可解析、字段齐全。

## 3. 伴随进程

- [x] 3.1 建立 `companion/app/main.py`。`GET /health` 返回 HTTP 200，JSON 含 `service=companion`、`status=up` 和 `request_id`。其他路径返回 HTTP 404。进程不读取 `DATABASE_URL`。用 pytest 请求 `/health` 和一个其他路径。

## 4. 前端壳

- [x] 4.1 用 Vite 与 React 建立 `frontend/`。根页面为 HTTP 200 的 HTML，包含「文献引路」「文献库」「阅读助手」。`/library` 与 `/reader` 只显示空状态，页面中没有 `input type="file"` 和提问用的文本框。用组件测试或构建后的 HTML 断言这三处文案，并断言不存在这两类控件。

## 5. 组装与启动

- [x] 5.1 添加 `docker-compose.yml` 与 Docker 构建文件。`db` 使用 `pgvector/pgvector:pg16`，首次启动执行 `CREATE EXTENSION IF NOT EXISTS vector`，不创建业务表。`api` 发布 8000，`companion` 发布 8001。应用镜像包含前端构建产物，且 `/health` 先于静态回退注册。核对 Compose 文件中的三个服务名和端口。
- [x] 5.2 若 README 的启动步骤还不能让人知道要填写哪些键，只补充键名说明，不改变 `docker compose up --build` 和 `http://localhost:8000/health`。按 README 填写 `.env` 后启动，`GET /health` 返回 HTTP 200，`GET http://localhost:8001/health` 返回 HTTP 200，`GET /` 的 HTML 含「文献引路」。
