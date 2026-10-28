## Purpose

描述文献引路骨架的对外行为：按仓库说明启动后可以检查应用与数据库是否连通，缺少必填配置时拒绝接受请求，并把每次访问记成一行 JSON。

## ADDED Requirements

### Requirement: Documented startup reaches health

系统 SHALL 能通过 `README.md` 中已写明的启动步骤启动，并且只使用由 `.env.example` 填写得到的值。启动完成后，8000 端口上的 `GET /health` MUST 返回 HTTP 200。

#### Scenario: Start from a clean checkout

- **WHEN** 操作者把 `.env.example` 复制为 `.env`，填写数据库连接，并运行 `README.md` 中的启动命令
- **THEN** `GET http://localhost:8000/health` 返回 HTTP 200

### Requirement: Missing required configuration refuses startup

数据库连接配置缺失或为空时，应用 MUST 拒绝接受连接。进程 MUST 以非 0 状态退出，并且输出 MUST 写明该配置项的名称。对话凭证或嵌入凭证为空时，MUST NOT 阻止本次启动。

#### Scenario: Database connection is absent

- **WHEN** 应用在数据库连接配置缺失或为空时启动
- **THEN** 进程在接受 HTTP 请求之前以非 0 状态退出，且输出写明所缺配置项的名称

#### Scenario: Gateway credentials are empty

- **WHEN** 应用带着可用的数据库连接启动，且对话凭证与嵌入凭证为空
- **THEN** 应用接受请求，并且 `GET /health` 返回 HTTP 200

### Requirement: Health check is unauthenticated

`GET /health` MUST NOT 要求凭证。成功时的响应体 MUST 表明应用已启动且数据库可达，并且 MUST 包含 `request_id`。响应体 MUST NOT 包含密码、令牌或网关凭证。

#### Scenario: Request without credentials

- **WHEN** 客户端在不带 `Authorization` 头的情况下调用 `GET /health`
- **THEN** 响应状态为 HTTP 200，响应体报告应用已启动、数据库可达，并包含 `request_id`

#### Scenario: Response does not leak secrets

- **WHEN** 客户端在成功启动后调用 `GET /health`
- **THEN** 响应体不包含数据库密码或任何网关凭证

### Requirement: Unreachable database is reported as down

数据库不可达时，`GET /health` MUST 返回 HTTP 503。响应体 MUST 将数据库报告为不可达，并且 MUST NOT 将其报告为可达。

#### Scenario: Database is stopped

- **WHEN** 应用正在运行且数据库不可达
- **THEN** `GET /health` 返回 HTTP 503，且响应体将数据库报告为不可达

### Requirement: Unknown API paths return not found

对本版本未定义的应用路径发起的请求 MUST 返回 HTTP 404。响应 MUST 包含 `request_id`。

#### Scenario: Unknown path

- **WHEN** 客户端调用 `GET /api/v1/missing`
- **THEN** 响应状态为 HTTP 404，且响应体包含 `request_id`

### Requirement: Each request writes one JSON log line

每个已完成的 HTTP 请求，应用 MUST 恰好写一行日志。该行 MUST 是单个 JSON 对象，包含 `time`、`level`、`request_id`、`method`、`path` 和 `status`。响应头 `X-Request-Id` MUST 等于该 `request_id`。该行 MUST NOT 包含密码或网关凭证。

#### Scenario: Health request is logged

- **WHEN** 客户端调用 `GET /health` 且响应已完成
- **THEN** 应用新写一行 JSON 日志，其 `request_id` 等于响应头 `X-Request-Id`，且 `method` 为 `GET`、`path` 为 `/health`、`status` 为该 HTTP 状态码

### Requirement: The shell exposes two empty entries

根页面 MUST 返回 HTTP 200 的 HTML，且包含文本 `文献引路`、`文献库` 和 `阅读助手`。每个入口 MUST 显示空状态。本版本 MUST NOT 提供上传控件或提问表单。

#### Scenario: Open the root page

- **WHEN** 客户端请求 `GET /`
- **THEN** 响应为 HTTP 200 的 HTML，且包含 `文献引路`、`文献库` 和 `阅读助手`

#### Scenario: Open either entry

- **WHEN** 访问者打开文献库入口或阅读助手入口
- **THEN** 该视图显示空状态，并且不提供文件上传或提问输入

### Requirement: Companion process answers only a liveness check

伴随进程 SHALL 在自己的端口上提供 `GET /health`，并返回 HTTP 200 的 JSON。响应体 MUST 将该进程标识为 `companion`，且 MUST 包含 `request_id`。该进程上的任何其他路径 MUST 返回 HTTP 404。伴随进程 MUST NOT 查询数据库，也 MUST NOT 调用外部文献服务。

#### Scenario: Companion health

- **WHEN** 客户端调用伴随进程的 `GET /health`
- **THEN** 响应为 HTTP 200 的 JSON，将该进程标识为 `companion`，并包含 `request_id`

#### Scenario: Companion has no other route

- **WHEN** 客户端调用伴随进程上除 `/health` 以外的任意路径
- **THEN** 响应状态为 HTTP 404
