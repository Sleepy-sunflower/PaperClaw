## Context

仓库里没有应用代码。`README.md` 已经规定启动方式：复制 `.env.example` 为 `.env`，执行 `docker compose up --build`，然后访问 `http://localhost:8000/health`。行为见 `specs/runtime-skeleton/spec.md`。技术栈沿用 `docs/文献引路-学期项目说明.md`：React/Vite、FastAPI、PostgreSQL + pgvector、独立的伴随进程。

## Goals / Non-Goals

**Goals:**

- 一条 Compose 命令同时启动数据库、应用和伴随进程。
- 应用按路由 → 服务 → 数据访问分层，健康检查走这条链路。
- 缺 `DATABASE_URL` 时进程以非 0 退出，并在输出中写出该键名。
- `/health`、404 和访问日志的字段与规格一致。

**Non-Goals:**

- 不建业务表，不实现登录、上传、检索、问答或 arXiv 工具。
- 不编写 `AGENTS.md`、`.cursor/rules/` 或其他工程规范。
- 不把对话网关和嵌入网关列为启动必填项。

## Decisions

### 进程与端口

Compose 包含三个服务：`db`、`api`、`companion`。

- `api` 发布 `8000`，与 README 一致。
- `companion` 发布 `8001`。规格要求调用方能访问它自己的 `/health`。
- `db` 使用 `pgvector/pgvector:pg16`。首次启动执行 `CREATE EXTENSION IF NOT EXISTS vector`。不建业务表。

备选是先用官方 Postgres 镜像，等向量检索时再换。现在换镜像，是为了避免下一份变更再改数据库服务。

### 配置

`.env.example` 只写键名，不写值：

- 启动必填：`DATABASE_URL`
- 数据库容器必填，且必须与 `DATABASE_URL` 中的账号一致：`POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`
- 预留、允许为空：`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`

应用在绑定端口之前读取环境变量。`DATABASE_URL` 缺失或空白时打印 `missing required setting: DATABASE_URL` 并退出。空的网关变量不参与这次检查。

备选是骨架阶段就强制网关密钥。那样没有课程网关凭证时，健康检查也无法演示。

### 目录与依赖方向

```text
backend/app/main.py            组装应用、中间件、静态文件
backend/app/config.py          读取环境变量
backend/app/api/health.py      HTTP 层
backend/app/services/health.py 组合检查结果
backend/app/db/ping.py         执行连通性查询
frontend/                      Vite + React 壳
companion/app/main.py          仅 /health
docker-compose.yml
.env.example
```

路由不写 SQL，数据访问不发起出站 HTTP。健康检查的数据库查询是 `SELECT 1`，超时 2 秒。连接失败时应用继续运行，由 `/health` 返回 HTTP 503，响应体为：

```json
{"status":"degraded","checks":{"app":"up","database":"down"},"request_id":"..."}
```

数据库可达时返回 HTTP 200，`status` 为 `ok`，`database` 为 `up`。

伴随进程的 `/health` 返回 HTTP 200：

```json
{"service":"companion","status":"up","request_id":"..."}
```

它不读取 `DATABASE_URL`，也不连接数据库。其余路径使用框架默认的 HTTP 404。

### 日志与请求标识

使用标准库写 stdout，不增加日志依赖。每个请求由中间件生成 UUID，放入响应头 `X-Request-Id`。请求结束后写一行 JSON，字段为 `time`、`level`、`request_id`、`method`、`path`、`status`。日志和响应体都不记录 `DATABASE_URL` 或网关密钥。

`/api` 下未定义的路径返回 JSON 404，并带上同一个 `request_id`。`/health` 在静态文件之前注册，避免被前端回退路由吃掉。

### 前端壳

Vite 构建产物打进应用镜像，由应用在 `/` 提供。页面有两个入口，路径为 `/library` 和 `/reader`，文案分别为「文献库」和「阅读助手」。两个视图只显示空状态，不放文件选择控件和提问输入框。

备选是本变更只交 API、页面以后再加。README 的验收是打开一个地址，而规格要求根页面包含产品名和两个入口，所以壳放在同一次构建里。

### 测试

用 pytest 覆盖缺配置退出、无认证的 `/health`、数据库不可达时的 503、未知路径 404，以及一行 JSON 日志。数据库不可达用一个无法连接的 `DATABASE_URL` 触发，不在测试里启动 Compose。Compose 本身由 README 的手动启动确认。

## Risks / Trade-offs

- [静态资源和接口共用一个进程，回退路由可能挡住 `/health`] → 先注册 `/health` 和 `/api`，只对余下的 GET 回退到 `index.html`。
- [`.env.example` 没有默认口令，Postgres 在口令为空时会启动失败] → README 已要求填写 `.env`。任务里确认 `POSTGRES_PASSWORD` 与 `DATABASE_URL` 使用同一个口令。
- [健康检查只做 `SELECT 1`，不能证明 pgvector 扩展可用] → 初始化脚本创建扩展；扩展是否真的可用留到向量检索那次变更验证。
- [伴随进程现在不是 MCP 协议] → 本次只证明它独立存活。工具发现放到后续变更，避免骨架引入 MCP SDK。

## Migration Plan

这是第一次提交可运行程序，没有旧数据。部署是 `docker compose up --build`。回滚是 `docker compose down`。数据库卷可以保留；本变更没有业务表需要迁移。
