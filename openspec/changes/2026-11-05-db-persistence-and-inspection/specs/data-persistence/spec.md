## Purpose

描述 Compose 栈里数据库数据的生命周期：停止栈不丢数据，重新启动后用户和文献仍在，清空数据需要操作者显式动作，数据文件不进仓库工作区。

## ADDED Requirements

### Requirement: Data survives a stack restart

`docker compose down`（不带 `-v`）之后再 `docker compose up -d`，数据库里已有的用户、会话、文献、片段和迁移记录 MUST 保留。启动完成后 `GET /health` MUST 返回 HTTP 200 且把数据库报告为可达。已应用的迁移 MUST NOT 再次执行，也 MUST NOT 清空或改写已有数据。

#### Scenario: Registered user and paper survive down and up

- **WHEN** 操作者注册一个用户、上传一份 PDF 并等到任务变为「已可检索」，然后执行 `docker compose down`，再执行 `docker compose up -d`
- **THEN** `GET /health` 返回 HTTP 200 且数据库为可达，用同一组用户名和密码调用 `POST /api/v1/sessions` 返回 HTTP 200 和令牌，`GET /api/v1/papers` 仍然列出该文件名

#### Scenario: Restart does not re-run applied migrations

- **WHEN** 库里已有注册用户和文献，操作者重新启动栈
- **THEN** 启动成功，`GET /health` 返回 HTTP 200，用户和文献的条数与重启前相同

### Requirement: Clearing data requires an explicit action

数据 MUST 只在操作者显式要求时才被清空。`docker compose down -v` MUST 删除保存数据的卷，之后启动的栈 MUST 使用一个空库，并重新执行初始化脚本与迁移。

#### Scenario: down -v clears the data

- **WHEN** 库里已有注册用户，操作者执行 `docker compose down -v`，再执行 `docker compose up -d`
- **THEN** `GET /health` 返回 HTTP 200，且用原先的用户名和密码调用 `POST /api/v1/sessions` 返回 HTTP 401，`code` 为 `unauthenticated`

### Requirement: Data stays out of the repository working tree

数据库文件 MUST 保存在 Docker 卷里，MUST NOT 写进仓库工作区。db 服务的端口 MUST NOT 对宿主机发布。

#### Scenario: git status stays clean

- **WHEN** 操作者启动栈、注册用户并上传一份 PDF，然后在仓库根目录执行 `git status`
- **THEN** 输出里没有数据库数据文件，也没有新增的未跟踪数据目录

#### Scenario: Database port is not reachable from the host

- **WHEN** 栈正在运行
- **THEN** 宿主机上没有为 db 服务发布的数据库端口，容器之外的程序无法直接连到该数据库
