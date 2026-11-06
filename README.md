# 文献引路

面向个人研究的文献阅读助手。用户上传自己的论文并向阅读助手提问，助手只依据该用户的文献库和本次检索到的出处回答。


## 本机运行

需要已安装 Git 与 Docker Desktop（含 Docker Compose）。

```powershell
git clone <仓库地址>
cd paperclaw
Copy-Item .env.example .env
docker compose up --build
```

macOS 或 Linux 把复制环境文件的那一行换成 `cp .env.example .env`。

填写 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`。`DATABASE_URL` 使用同一套账号，主机名为 `db`，端口为 `5432`。`LLM_*` 和 `EMBEDDING_*` 可以留空。

启动后访问 [http://localhost:8000/health](http://localhost:8000/health)。返回应用与数据库的连通状态即表示启动成功。

密钥只写在本机的 `.env` 里。`.env.example` 只保留键名。

## 数据保存

数据库数据保存在 Docker 卷 `pgdata` 里。`docker compose down` 之后再 `docker compose up -d`，用户、会话、文献、片段和迁移记录都还在，用原先的用户名和密码仍能登录。只有 `docker compose down -v` 会删掉这个卷，把库清空；下一次启动重新执行 `db/init` 和迁移。数据文件不进仓库工作区，`git status` 保持干净。数据库端口不对宿主机发布。

启动顺序是 db 就绪 → 一次性 `migrate` 容器执行迁移并退出 → api 与 worker 启动。`docker compose ps` 里看到 `migrate` 是 `Exited (0)` 属于正常。

改了 `.env` 里的 `POSTGRES_PASSWORD` 之后，卷里存的仍是首次初始化时的口令，`GET /health` 会把数据库报成不可达。两条路：`docker compose down -v` 重新起（会清空数据），或者在容器里执行 `ALTER ROLE <数据库用户名> PASSWORD '<新口令>'` 让两边一致。

## 查看数据库内容

在仓库根目录执行，不需要手动进容器，也不需要知道数据库口令。

```powershell
python tools/db_inspect.py
```

输出会打印到终端，同时写进 `tmp/db-inspect.txt`（终端把中文显示成乱码时打开这个文件看）。它分节显示用户、会话、文献、入库任务和片段正文摘要，只显示白名单字段：不含 `password_hash`、`token_hash`、PDF 字节和向量数值。脚本只读，不改数据，不读取也不修改 `.env`。栈没有启动时会写明原因并以非 0 退出码结束。

查看独立测试栈时指定项目名和环境变量文件：

```powershell
python tools/db_inspect.py --project paperclaw-e2e --env-file tests/e2e-compose.env
```

## 注册、登录和登出

打开 http://localhost:8000/ 。还没有登录时会进入登录页。这一页没有「文献引路」大标题，也没有文献库和阅读助手菜单。注册和登录在同一页。

用户名是 1 至 32 个字符，只含小写字母、数字和连字符。密码是 1 至 72 个字符。先注册，再用同一组用户名和密码登录。登录成功后进入文献库，这时才出现大标题和两个菜单。文献库显示当前用户名；还没有文献时显示空状态。

菜单里的「登出」会结束这次登录，并回到登录页。关掉浏览器再打开，登录仍然保留，直到点击登出。

注册、登录或登出的请求因为网络中断失败时，页面留在原处并显示错误，不会一直显示加载中。文献库读取当前会话超过 10 秒同样显示错误，刷新页面再试。

## 上传文献

登录后在文献库选择一份 PDF 并点击「上传」。上传马上返回，处理由另一个进程完成，页面用纯文本显示任务的当前状态：「待处理」「处理中」「已可检索」「失败」，以及处理步骤「抽字」「切块」「嵌入」「写入」。状态是页面轮询看到的，处理进程在两次轮询之间就跑完时，中间的状态可能不出现，页面直接显示「已可检索」和四个步骤。状态成为「已可检索」后，页面列出你的文件名；处理失败时留在文献库并显示错误。

文献库只列出当前用户已可检索的文献。别人的文献不会出现在你的列表里，也无法用你的令牌读到。同一份 PDF 再次上传只保留一份文献。

处理进程使用 `.env` 里的 `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL` 和 `EMBEDDING_DIM`。这些值可以留空，留空时仍能上传，但任务会变为「失败」。密钥只写在本机 `.env` 里，不出现在页面和接口响应中。

## 测试

在仓库根目录执行。其中一条用例会执行 `docker compose up --build -d`，并检查 http://localhost:8000/health 里数据库为连通。其余需要数据库的用例另起一个测试库，不使用 Compose 里的库。不需要再设置环境变量。需要本机 Docker 已启动，并且 `.env` 已按上一节填好。

```powershell
pytest --junitxml=test-reports/junit.xml
```

退出码 `0` 表示通过。报告写在 `test-reports/junit.xml`。

前端组件测试在 `frontend/` 目录执行 `npm test`。退出码 `0` 表示通过。

端到端真实上传验证（真实 Compose 栈 + 本地桩嵌入端点，不使用真实网关、不改本机 `.env`）在仓库根目录执行 `python tests/e2e_real_upload.py`。生成的 PDF 样本和桩日志在 `tmp/` 里，可以打开查看。

数据持久与数据库可视化脚本的端到端验证（注册、上传、`down` 后重新 `up`、再运行 `tools/db_inspect.py`）执行 `python tests/e2e_persistence_and_inspect.py`。它用同一个独立 Compose 项目名，结束时 `down -v` 拆栈，报告写在 `tmp/db-inspect-e2e.txt`。

