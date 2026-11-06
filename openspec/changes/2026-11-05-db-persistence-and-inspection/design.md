## Context

动机见 proposal.md - Why。当前状态与约束：

- `docker-compose.yml` 的 db 服务是 `pgvector/pgvector:pg16`，只绑定挂载 `./db/init` 到 `/docker-entrypoint-initdb.d`，数据目录 `/var/lib/postgresql/data` 落在容器可写层，`down` 即丢。db 没有 `ports`，宿主机连不进去。
- 迁移由 `backend/app/db/migrate.py` 在 api 与 worker 启动时执行，已应用版本记录在库内的 `schema_migrations` 表里，`migrate_up` 对已应用版本跳过。因此只要数据目录保留，重启不会重复迁移。
- `db/init/01-vector.sql` 只在数据目录为空（首次初始化）时执行；`002_papers_chunks.up.sql` 里也有 `CREATE EXTENSION IF NOT EXISTS vector`，所以老卷升级和新卷初始化都能拿到 `vector` 扩展。
- 表结构：`users(id, username, password_hash, created_at)`、`sessions(id, user_id, token_hash, created_at)`、`papers(id, user_id, filename, content_sha256, created_at)`、`chunks(id, paper_id, user_id, page, content, embedding vector(2048), created_at)`、`ingest_tasks(id, user_id, filename, content_sha256, pdf bytea, status, log text[], paper_id, created_at)`。
- `.cursor/rules/9-e2e-verification.mdc` 要求：端到端驱动脚本和桩放 `tests/`（文件名不以 `test_` 开头），产物写 `tmp/`（已 gitignore），不读取也不修改本机 `.env`，用独立项目名 `-p paperclaw-e2e` 加 `--env-file tests/e2e-compose.env` 起停，结束时 `down -v`。
- 本机是 Windows + Git Bash，Python 解释器为 `/d/Tools/miniconda3/python.exe`；控制台默认编码 GBK，中文输出需要显式改用 UTF-8（上一次端到端验证遇到过乱码）。
- `pytest` 用例使用 `tests/conftest.py` 另起的测试库容器，不使用 Compose 里的库，所以数据持久化不影响现有用例。

## Goals / Non-Goals

**Goals:**

- 只改 Compose 配置就让数据在 `down` / `up` 之间保留，并保留 `down -v` 作为唯一的显式清空动作。
- 让操作者用一条命令看到库里的用户与文献正文摘要，不需要懂 psql，也不需要知道数据库口令。
- 让「注册 + 上传 + 重启 + 可视化」这条验收路径可以一键复跑，并且不碰本机 `.env`。

**Non-Goals:**

- 不做备份、导出、快照或卷迁移工具。
- 不改数据库表结构、迁移文件、API 契约和前端页面。
- 不给数据库发布宿主机端口，也不引入 pgAdmin 之类的图形客户端。
- 不处理 `ingest_tasks.pdf` 长期占用卷空间的清理策略（记为已知限制）。

## Decisions

### 迁移先跑完，再起 api 和 worker

空卷首次启动时，api 与 worker 会同时执行 `migrate_up`，两个并发的 `CREATE TABLE IF NOT EXISTS schema_migrations` 会撞上 `pg_type_typname_nsp_index`（`duplicate key value ... (schema_migrations, 2200)`），api 进程直接退出，`GET /health` 一直不可达。这个竞争在加卷之前就存在，只是每次空卷启动都在掷硬币；本次端到端验证里复现了一次。

做法按「一个先一个后」：新增一次性 `migrate` 服务（`command: ["python", "-m", "app.db.migrate"]`，`depends_on: db: service_healthy`），api 与 worker 都加 `depends_on: migrate: condition: service_completed_successfully`。migrate 成功退出后 `schema_migrations` 已存在、版本已记录，api 与 worker 各自的 `migrate_up` 只会跳过，不再有并发建表。

- 备选：在 `migrate_up` 事务开头加 `pg_advisory_xact_lock`。同样能解决，但启动顺序对操作者不可见；用一个服务把顺序摆出来，`docker compose ps` 里能直接看到 migrate 的退出码。
- 备选：给 api 与 worker 加 `restart: on-failure`。只是让崩溃静默重试，日志里仍留错误。
- api 与 worker 启动时仍各自调用 `migrate_up`，这样不经 Compose 启动（例如 pytest 另起的测试库）也能自动迁移。

### 数据持久化用命名卷，不用绑定挂载

db 服务增加 `- pgdata:/var/lib/postgresql/data`，顶层增加 `volumes: { pgdata: {} }`；`./db/init` 的绑定挂载保留。

- 备选：绑定挂载到 `./db/data`。否掉，因为 PostgreSQL 数据文件会进仓库工作区，Windows 上还有权限与 I/O 问题，`git status` 也不再干净。
- 备选：让操作者自备外部数据库。否掉，README 的承诺是 `docker compose up --build` 一条命令跑起来。
- 命名卷同时满足「重启保留」和「`down -v` 显式清空」，与 rule 9 的拆栈方式一致。

### 可视化脚本放 `tools/db_inspect.py`

新建 `tools/` 目录放这一个脚本。它是 README 里写给操作者的日常命令，不是端到端测试的辅助件，因此不放 `tests/`；`tests/` 继续按 rule 9 只放驱动脚本和桩。脚本只用标准库（`argparse`、`subprocess`、`pathlib`、`sys`），不引入新依赖。

### 通过 `docker compose exec -T db psql` 读数据

命令形如 `docker compose [-p <project>] [--env-file <path>] exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "<SQL>"'`。用户名和库名在容器内由 db 服务自己的环境变量展开，宿主机侧不需要知道它们，脚本也就完全不用读 `.env`。`-T` 关掉伪终端，`-At` 输出无表格边框的裸值，便于脚本拼装可读文本。

- 备选：给 db 发布 5432 端口，脚本用 `psycopg` 连。否掉，因为它把数据库暴露到宿主机（与「db 不发布端口」的现状相悖），并且要求脚本拿到口令，也就是要读 `.env` 或环境变量文件。
- 备选：只提供一段 README 里的 `docker compose exec db psql` 命令让操作者手敲。否掉，用户明确要求一个脚本，而且手敲 SQL 无法保证不查出 `password_hash`。

### 查询按字段白名单，输出分节

每一节单独查询，只取需要的列，不用 `SELECT *`：

- 用户：`username`、`created_at`
- 会话：所属 `username`、`created_at`（以及总条数）
- 文献：`filename`、所属 `username`、`content_sha256` 前 12 位、该文献的片段数、`created_at`
- 入库任务：`filename`、所属 `username`、`status`、`log`
- 片段：所属 `filename`、`page`、`substr(content, 1, 120)`、`vector_dims(embedding)`

`password_hash`、`token_hash`、`pdf` 字节和 `embedding` 数值都不出现在任何查询里，从源头保证输出不泄露。每节没有行时打印中文空状态（例如「还没有用户。」），而不是留一个空标题。

### 输出同时写 `tmp/db-inspect.txt`

脚本先 `sys.stdout.reconfigure(encoding="utf-8")` 再打印，并把同一份内容写进 `tmp/db-inspect.txt`。Windows 控制台默认 GBK，中文会显示成乱码；`tmp/` 已 gitignore，操作者可以直接打开文件看。命令行参数：`--project`（Compose 项目名，默认日常栈）、`--env-file`（默认不传）、`--output`（默认 `tmp/db-inspect.txt`）。

### 栈不可用时给中文提示并非 0 退出

`docker compose exec` 在栈没启动时返回非 0 并输出英文错误。脚本捕获后打印一行中文说明（先运行 `docker compose up -d`）并以退出码 1 结束，不把 Docker 的堆栈直接抛给操作者。

### 验收用新的端到端脚本，复用已有的桩

新增 `tests/e2e_persistence_and_inspect.py`，沿用 rule 9 的约定（项目名 `paperclaw-e2e`、`tests/e2e-compose.env`、`tests/stub_embeddings.py`、产物进 `tmp/`、结束时 `down -v` 并停桩）。流程：预清理 `down -v` → 起桩 → `up --build -d` → 注册用户、上传 PDF、轮询到「已可检索」 → `down`（不带 `-v`） → `up -d` → 用同一组用户名密码登录得到 HTTP 200 且列表仍含该文件名 → 子进程运行 `tools/db_inspect.py --project paperclaw-e2e --env-file tests/e2e-compose.env` → 断言输出含用户名、文件名和 PDF 正文里的词 → `down -v`。

同时给 `tests/e2e_real_upload.py` 在 `up` 之前加一次 `compose("down", "-v")` 预清理：数据持久化后，一次中断留下的卷会让「文献库只列出这一个文件名」这类断言失败。

### 独立测试栈把宿主机端口挪到 18000

`docker-compose.yml` 把 api 发布在 8000、companion 发布在 8001，独立项目名并不隔离宿主机端口：只要操作者的日常栈在跑，端到端脚本就起不来，与 rule 9 的判据「日常栈的容器不受影响」冲突（这个冲突在本次改动之前就已存在，只是日常栈当时恰好没在运行）。

做法：新增 `tests/e2e-ports.yml` 覆盖文件，用 `ports: !override` 把 api 改成 `18000:8000`、companion 改成 `18001:8001`；两个端到端脚本的 `compose()` 都带上 `-f docker-compose.yml -f tests/e2e-ports.yml`，`BASE` 改成 `http://localhost:18000`。db 与 worker 本来就不发布端口，不需要覆盖。

- 备选：停掉日常栈再跑验证。否掉，因为它把「跑端到端」的前提变成「先动操作者正在用的栈」。
- 备选：在 `docker-compose.yml` 里把端口写成 `${API_PORT:-8000}` 插值。否掉，因为那是为测试在产品配置里加旋钮，覆盖文件能把测试专用配置留在 `tests/` 里。
- `!override` 需要 Docker Compose 2.24 以上；本机是 v5.5.1。必须显式覆盖，否则 Compose 对 `ports` 这类多值项是追加合并，8000 仍会被绑定。

## Risks / Trade-offs

- 操作者改了 `.env` 里的 `POSTGRES_PASSWORD`，卷里的口令仍是旧的，api 与 worker 连不上，`GET /health` 变 503 → README 写明：改口令要么 `docker compose down -v`（会清空数据），要么在容器里执行 `ALTER ROLE ... PASSWORD ...`；可视化脚本报数据库不可达时也提示这两条路。
- 老环境升级后原先的数据不会回来（旧行为本来就不保存） → 无需数据迁移；README 说明从本版本开始数据才保留。
- 卷会随上传增长，`ingest_tasks.pdf` 存的是整份 PDF 字节 → 本次不处理，作为已知限制记在 design 与 README 之外不做承诺。
- 操作者可能在多个 Compose 项目名下同时跑栈，脚本默认指向日常栈，看到的不是预期的库 → 提供 `--project` 与 `--env-file`，并在输出开头打印本次读取的项目名与环境变量文件。
- `docker compose exec` 需要 db 容器正在运行；容器处于 health: starting 时查询可能失败 → 脚本把失败当作「数据库不可达」处理，提示稍后重试，不写半截输出文件。

## Migration Plan

1. 修改 `docker-compose.yml`：db 服务加 `pgdata:/var/lib/postgresql/data`，顶层加 `volumes: pgdata: {}`；新增一次性 `migrate` 服务，api 与 worker 都等它成功退出后再启动。
2. 操作者执行 `docker compose up -d`：Compose 创建命名卷，PostgreSQL 发现数据目录为空，执行 `db/init` 与迁移，之后数据落在卷里。已有容器会被重建，旧的可写层数据本来就不保存，无需迁移动作。
3. 新增 `tools/db_inspect.py`，在 README 的「本机运行」之后补一节说明数据持久与查看命令。
4. 新增 `tests/e2e_persistence_and_inspect.py`，给 `tests/e2e_real_upload.py` 加预清理。
5. 回滚：删掉 `docker-compose.yml` 里的卷条目即恢复旧行为；需要清理卷时执行 `docker compose down -v` 或 `docker volume rm paperclaw_pgdata`。
