## Why

文献引路还没有可启动的程序。后续的登录、文献库、检索、阅读助手和 arXiv 检索都要落在同一套进程、配置和日志上。现在先交出这个壳，避免第一批业务代码各自决定目录、环境和启动方式。

## What Changes

- 用 Docker Compose 一条命令启动 PostgreSQL（含 pgvector）、应用接口和 MCP 进程。
- 应用在缺少必填环境变量时拒绝启动，并指出缺少的键名。
- 提供免认证的 `GET /health`，返回应用与数据库的连通状态。
- 每个 HTTP 请求写一行 JSON 日志，包含请求标识。
- 应用接口托管前端构建产物。页面只显示产品名和两个空入口：文献库、阅读助手。
- MCP 进程只提供存活检查，不实现 `arxiv_search` 或 `arxiv_get`。
- 补齐 `.env.example`，使现有 `README.md` 的启动步骤可以执行。

本次不实现注册登录、PDF 上传、切块、向量检索、阅读助手、阅读引导技能和 arXiv 工具。工程规范由另行变更完成，不包含在本次任务中。

## Capabilities

### New Capabilities

- `runtime-skeleton`: 可复现启动、缺配置即失败、免认证健康检查、JSON 访问日志，以及只含空入口的前端壳。

### Modified Capabilities

- 无。仓库中还没有已归档的能力规格。

## Impact

- 新增后端、前端、MCP 服务和 `docker-compose.yml`。仓库目前只有 `README.md`、`.gitignore` 和项目说明。
- 新增公开接口 `GET /health`。数据库使用 PostgreSQL 与 pgvector 镜像，本变更不建业务表。
- `.env.example` 列出数据库连接和日后网关要用的键名。骨架启动只强制要求数据库连接；对话与嵌入密钥留空时不影响本次启动。
- `README.md` 已写明 `docker compose up --build` 和 `http://localhost:8000/health`。实现必须与这段说明一致。
