## 1. 数据持久化

- [x] 1.1 在 `docker-compose.yml` 的 db 服务里加上 `- pgdata:/var/lib/postgresql/data`，并在文件顶层声明 `volumes:` 下的 `pgdata:`，保留原有的 `./db/init` 挂载。验证：`docker compose config` 的输出里 db 的 volumes 同时含 `./db/init` 与 `pgdata:/var/lib/postgresql/data`，db 仍然没有 `ports`；`docker compose up -d` 后 `docker volume ls` 能列出以当前项目名开头的 `pgdata` 卷。
- [x] 1.2 手动确认「重启保留、显式清空」：`docker compose up -d` 起栈，用 `POST /api/v1/users` 注册一个用户，执行 `docker compose down`（不带 `-v`）后再 `docker compose up -d`。验证：`GET /health` 返回 HTTP 200 且数据库为 up，用同一组用户名和密码调用 `POST /api/v1/sessions` 返回 HTTP 200；随后 `docker compose down -v` 再 `up -d`，同一组凭证返回 HTTP 401 且 `code` 为 `unauthenticated`。
- [x] 1.3 确认数据不进仓库工作区：栈运行期间注册用户并上传一份 PDF，然后在仓库根目录执行 `git status`。验证：输出里没有任何数据库数据文件或新增的数据目录，只有本次改动的源码与文档。
- [x] 1.4 让迁移先跑完再起 api 与 worker（空卷首次启动时两者并发执行 `CREATE TABLE IF NOT EXISTS schema_migrations` 会撞 `pg_type_typname_nsp_index`，api 直接退出）：新增一次性 `migrate` 服务（`command: ["python", "-m", "app.db.migrate"]`，`depends_on: db: service_healthy`），给 `backend/app/db/migrate.py` 加 `__main__` 入口，api 与 worker 都加 `depends_on: migrate: condition: service_completed_successfully`。验证：清空数据卷后连续多次 `docker compose up --build -d`，`paperclaw-migrate-1` 都以 0 退出，api 与 worker 随后启动，`GET /health` 每次都在轮询内返回 HTTP 200，日志里没有 `duplicate key value`。

## 2. 数据库可视化脚本

- [x] 2.1 新增 `tools/db_inspect.py`，只用标准库：`argparse` 提供 `--project`、`--env-file`、`--output`（默认 `tmp/db-inspect.txt`），通过 `docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "<TAB>"'` 把 SQL 从标准输入交给容器里的 psql（避免引号转义），按字段白名单分节输出用户、会话、文献、入库任务和片段（页码 + `substr(content, 1, 120)` + `vector_dims(embedding)`），先 `sys.stdout.reconfigure(encoding="utf-8")` 再打印，并写入 `--output` 指定的文件，输出开头打印本次读取的项目名与环境变量文件。验证：栈运行且库里有数据时执行 `python tools/db_inspect.py`，退出码为 0，标准输出与 `tmp/db-inspect.txt` 里都能看到用户名、文件名、任务状态和片段正文摘要，且搜不到 `password_hash` 的值、`token_hash` 的值和向量数值。
- [x] 2.2 处理空库与栈未启动两种情况：每一节没有行时打印中文空状态，`docker compose exec` 返回非 0 时打印一行中文说明（先运行 `docker compose up -d`）并以退出码 1 结束，不抛出未处理的异常堆栈。验证：清空数据后运行脚本，退出码为 0 且各节显示空状态；`docker compose down` 之后运行脚本，退出码非 0 且输出是中文提示。
- [x] 2.3 确认脚本只读：连续运行两次，中间不改数据。验证：两次输出的用户数、文献数、片段数完全相同，运行后 `GET /health` 仍返回 HTTP 200，本机 `.env` 内容不变。

## 3. 端到端验证

- [x] 3.1 新增 `tests/e2e_persistence_and_inspect.py`，沿用 `.cursor/rules/9-e2e-verification.mdc` 的约定（项目名 `paperclaw-e2e`、`--env-file tests/e2e-compose.env`、复用 `tests/stub_embeddings.py`、产物写 `tmp/`、`finally` 里 `down -v` 并停桩）。流程：预清理 `down -v` → 起桩 → `up --build -d` → 注册用户、上传 PDF、轮询到「已可检索」 → `down`（不带 `-v`） → `up -d` → 用同一组凭证登录 → 子进程运行 `tools/db_inspect.py --project paperclaw-e2e --env-file tests/e2e-compose.env` → 逐项 `check()` 打印 PASS/FAIL 并按失败数决定退出码。验证：`python tests/e2e_persistence_and_inspect.py` 退出码为 0，检查项覆盖「重启后登录返回 200」「重启后列表仍含该文件名」「可视化输出含用户名」「可视化输出含文件名」「可视化输出含 PDF 正文里的词」，全部 PASS；跑完 `git status` 干净，本机 `.env` 内容不变，`tmp/` 里能看到 PDF 样本、桩日志和 db-inspect 输出。
- [x] 3.2 给 `tests/e2e_real_upload.py` 在 `up --build -d` 之前加一次 `compose("down", "-v")` 预清理，避免上一次中断留下的数据卷影响断言。验证：连续执行两次 `python tests/e2e_real_upload.py`，两次都是全部 PASS、退出码 0。
- [x] 3.3 新增 `tests/e2e-ports.yml`，用 `ports: !override` 把 api 改成 `18000:8000`、companion 改成 `18001:8001`；两个端到端脚本的 `compose()` 都带上 `-f docker-compose.yml -f tests/e2e-ports.yml`，`BASE` 改成 `http://localhost:18000`。验证：日常栈正在运行（占着 8000 和 8001）时执行 `python tests/e2e_persistence_and_inspect.py`，独立栈仍能起来并全部 PASS，`docker ps` 里日常栈的容器一直在运行。

## 4. 文档与校验

- [x] 4.1 在 `README.md` 的「本机运行」之后补一节，写明：数据从本版本起保存在 Docker 卷里，`docker compose down` 不丢数据，`docker compose down -v` 才会清空；改了 `POSTGRES_PASSWORD` 之后要么 `down -v`（会清数据）要么在容器里执行 `ALTER ROLE`；再给出查看数据库内容的命令 `python tools/db_inspect.py` 和输出文件 `tmp/db-inspect.txt`。验证：照 README 里的命令逐条执行能跑通，文档里没有任何真实密钥或口令。
- [x] 4.2 校验本次变更的规划与实现一致：`openspec validate --strict --type change "2026-11-05-db-persistence-and-inspection"`，并跑一遍 `pytest --junitxml=test-reports/junit.xml`。验证：validate 无错误，pytest 退出码为 0（既有用例不受数据卷改动影响）。
