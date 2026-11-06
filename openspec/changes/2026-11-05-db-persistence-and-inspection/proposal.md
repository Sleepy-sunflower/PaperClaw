## Why

现在 `docker-compose.yml` 里的 db 服务只挂载了 `./db/init`，PostgreSQL 的数据目录没有卷。操作者执行 `docker compose down` 之后，注册的用户、会话、文献、片段和迁移记录全部消失，下一次启动等于重新装一遍。同时，库里的内容只能靠手动进容器敲 psql 才看得到，没有一条现成的命令能回答「现在库里有哪些用户和哪些文献内容」。

## What Changes

- db 服务增加一个命名卷保存 PostgreSQL 数据目录，并在 `docker-compose.yml` 顶层声明该卷。`docker compose down` 再 `docker compose up -d` 之后，已注册的用户、会话、文献、片段和 `schema_migrations` 记录都保留；用户可以用同一组用户名和密码再次登录，文献库仍列出已可检索的文献。
- `docker compose down -v` 仍然是显式清空数据的途径，删除卷后下一次启动重新执行初始化脚本和迁移。
- 数据 MUST 只存在 Docker 卷里，不写进仓库工作区；db 服务的端口继续不对宿主机发布。
- 新增数据库可视化脚本 `tools/db_inspect.py`：通过 `docker compose exec -T db psql` 读取，按节显示用户、会话、文献、入库任务和片段正文摘要，输出到标准输出并写入 `tmp/db-inspect.txt`。它 MUST NOT 显示 `password_hash`、`token_hash`、PDF 字节和向量数值，也 MUST NOT 读取或修改本机 `.env`。
- 新增端到端验证脚本 `tests/e2e_persistence_and_inspect.py`：在独立 Compose 项目里注册用户、上传测试 PDF，`down`（不带 `-v`）后重新 `up`，确认仍能登录且文献还在，再运行可视化脚本并确认输出里能看到用户名和 PDF 正文。
- `tests/e2e_real_upload.py` 在启动前先执行一次 `down -v` 预清理，避免上一次中断留下的数据卷影响「文献库只列出这一份文件名」这类断言。
- `README.md` 增加数据持久说明（含改密码需要 `down -v` 的提醒）和查看数据库内容的命令。

## Capabilities

### New Capabilities

- `data-persistence`: Compose 栈里的数据库数据在停止和重新启动之间保留，清空数据需要显式动作，数据文件不进仓库工作区。
- `db-inspection`: 操作者用一条命令查看库里的用户、文献和片段正文摘要，输出不泄露凭证与向量数值。

### Modified Capabilities

（无。已有 capability 的对外行为不变：`runtime-skeleton` 的启动与健康检查、`user-login`、`user-logout`、`paper-ingest` 的接口契约都保持原样，只是数据在重启后仍然存在。）

## Impact

- `docker-compose.yml`：db 服务增加 `volumes` 条目，顶层增加 `volumes` 声明。
- 新文件：`tools/db_inspect.py`、`tests/e2e_persistence_and_inspect.py`。
- 改动文件：`tests/e2e_real_upload.py`（预清理）、`README.md`（持久说明与查看命令）。
- 后端代码、API 路径、数据库表结构和迁移文件不变；`pytest` 用例不受影响，它们使用 `tests/conftest.py` 另起的测试库，不使用 Compose 里的库。
- 操作者影响：已有环境第一次启动本版本时，原先随容器消失的数据不会自动回来；改 `POSTGRES_PASSWORD` 后需要 `down -v` 或手动改库里的口令，细节见 design.md。
