## Context

动机见 `proposal.md` 的 Why。这里只写影响做法的现状与约束。

`frontend/src/pages/LibraryPage.tsx` 用一个 400 毫秒的轮询读取 `GET /api/v1/paper-tasks/{task_id}`，只在观察到的状态与上一条不同时把它追加进 `statuses`。服务端 `ingest_tasks` 只有 `status` 和 `log text[]` 两列，没有状态历史。`log` 已经有「抽字」「切块」「嵌入」「写入」四条，处理进程每做一步就追加一条。

`tests/conftest.py` 的 `test_database_url` 会自己起一个名为 `paperclaw-pytest-pg`、宿主机端口 54329 的 pgvector 容器，与 Compose 栈的库不是同一个。`.cursor/rules/4-testing.mdc` 要求用例不依赖执行顺序、运行前后清理自己写入的数据。`.cursor/rules/9-e2e-verification.mdc` 要求端到端驱动脚本不读取也不修改本机 `.env`，并且明确这类脚本不算 Scenario 覆盖。

`tools/db_inspect.py` 是面向操作者的命令行工具，不是 Python 包：`tools/` 下没有 `__init__.py`。它把访问数据库的动作全部收在 `run_sql(command, sql) -> (ok, stdout, stderr)` 一个函数里，`build_report(command, project, env_file) -> (report, exit_code)` 只依赖这个返回值，空库和停栈两个分支都在 `build_report` 内。

`frontend/src/Shell.tsx` 的登出已经自己捕获异常并留在原页，`frontend/src/App.test.tsx` 里 Scenario `Logout stays when the request fails` 同时覆盖 `fetch` 抛错和 HTTP 500。登录页的组件测试也写在 `App.test.tsx`，没有单独的 `LoginPage.test.tsx`。

## Goals / Non-Goals

**Goals:**

- 让规格、实现和用例三者对同一件事说法一致：页面显示什么状态，用例就断言什么。
- 让七个 Scenario 各有一条 `tests/` 下的 `test_` 用例或 `frontend/` 下的 `.test.tsx`，并且能在只按 `README.md`「测试」执行一次命令时跑到。
- 网络失败和请求挂起时，三个页面都落到错误状态，不停在加载中。

**Non-Goals:**

- 不给 `ingest_tasks` 增加状态历史列，不改任何接口响应字段，不改数据库结构，因此本次没有迁移。
- 不把 `tools/db_inspect.py` 改成包，也不给它加新的命令行参数。
- 不给上传和任务轮询加超时：上传超时会让用户以为文件没传上去，轮询已经有 `catch` 并停在当前页。
- 不重写端到端驱动脚本。它们继续覆盖真实的 Compose 行为，只是不再被当作 Scenario 的唯一覆盖。

## Decisions

### 放宽页面状态的规格，而不是让服务端保存状态轨迹

`paper-ingest` 的 Requirement `Library prints the task and lists only ready papers` 改成：页面 MUST 以纯文本显示任务的当前状态（「待处理」「处理中」「已可检索」「失败」中的一个）和日志步骤，状态按轮询观察到的顺序追加；轮询之间被跳过的中间状态 MUST NOT 让页面停在旧状态、留白或一直加载。Scenario `Library shows the task log` 的 THEN 改成断言「已可检索」和四条日志步骤都出现，并且页面没有空白。另加 Scenario `Skipped intermediate status does not stall the page`，把「第一次轮询就看到已可检索」这条路径写成规格，作为组件测试的来源。

理由：`log` 里已经有「抽字」「切块」「嵌入」「写入」，操作者看得出自己那份文献走到哪一步；「处理中」这三个字本身不传递更多信息。要让它必然出现，得给 `ingest_tasks` 加一列状态历史或把状态变化也写进 `log`，两者都要迁移、改处理进程、改接口响应，换来的只是页面上多一个词。

备选：(1) 服务端记录状态轨迹并由接口返回 —— 用户已否决，改动面与收益不匹配。(2) 前端在上传成功后本地补一条「处理中」 —— 否决，页面会显示一个服务端从未进入过的状态，属于造假。

### 依赖 Docker 的 Scenario 用机制级断言覆盖，不在 pytest 里跑 `docker compose down -v`

四条 `data-persistence` 的 Scenario 这样落用例，全部放在 `tests/normal/` 与 `tests/failure/`，用已有的 `test_database_url`：

- `Restart does not re-run applied migrations`：`migrate_up` 一次，往 `users` 插一行哨兵并记下 `schema_migrations` 的全部版本，再 `migrate_up` 一次，断言哨兵还在、版本集合不变且没有重复。这直接断言「已应用的迁移不再执行」这个机制本身，比端到端里「重启后数据还在」更贴近 Scenario。
- `down -v clears the data`：注册并登录一个用户，`TRUNCATE sessions, users CASCADE` 清空（等价于换成一个空卷，因为卷里只有数据库数据），再用同一组用户名和密码调用 `POST /api/v1/sessions`，断言 HTTP 401 且 `code` 为 `unauthenticated`。等价关系写在用例的 docstring 里。
- `git status stays clean`：解析 `docker compose config --format json` 的输出，断言 db 的 `volumes` 里有一项 `type` 为 `volume`、`target` 为 `/var/lib/postgresql/data`，并且仓库根目录下不存在 `pgdata`、`data`、`db/data` 这类数据目录；再断言 `git status --porcelain` 列出的路径里没有这些目录。
- `Database port is not reachable from the host`：同一份 `docker compose config --format json` 输出里，断言 db 服务没有 `ports`。

理由：pytest 必须能在日常栈没有运行、不读本机 `.env`、不删操作者数据的前提下跑完。真在 pytest 里执行 `docker compose down -v` 会删掉操作者的卷，也会和正在运行的栈抢端口。机制级断言测的是同一条约束（数据在卷里、卷不发布端口、清空后凭证失效），且每次运行结果一致。

备选：把这些 Scenario 留给 `tests/e2e_persistence_and_inspect.py` —— 否决，`9-e2e-verification.mdc` 明确端到端驱动脚本不算 Scenario 覆盖，这正是审查者指出的缺口。

### `tools/db_inspect.py` 的两个分支用替身 `run_sql` 覆盖

用例把 `tools/` 加进 `sys.path` 后 `import db_inspect`，用 `monkeypatch.setattr(db_inspect, "run_sql", fake)` 提供固定返回值，然后断言 `build_report` 的文本和退出码：

- `Empty database`：探测查询返回成功，五节查询都返回空字符串，断言退出码为 0，报告里出现「还没有用户。」「还没有会话。」「还没有文献。」「还没有入库任务。」「还没有片段。」，且不含 `Traceback`。
- `Stack is stopped`：探测查询返回失败并带一段 `docker compose exec` 的错误输出，断言退出码为 1，报告里出现「请先运行 docker compose up -d」，且不含 `Traceback`。

理由：这两个分支只依赖 `run_sql` 的三元组返回值，替身足以驱动，不需要真的起栈或停栈。不给 `tools/` 加 `__init__.py`：脚本是面向操作者的命令，加包结构会让 `python tools/db_inspect.py` 的相对导入语义变复杂，收益为零。

### 超时用 `AbortController`，超时值导出成模块常量

`LibraryPage.tsx` 里读取 `GET /api/v1/sessions/current` 的 `fetch` 带上 `AbortController` 的 `signal`，`setTimeout` 到 `SESSION_TIMEOUT_MS`（导出该常量）时调用 `abort()`，`finally` 里清掉定时器。`abort` 触发的 `DOMException` 和 `fetch` 抛出的 `TypeError` 走同一条路径：置 `failed`，页面显示已有的「文献列表没有载入。可能是网络中断。刷新页面再试。」。

`LoginPage.tsx` 的 `onLogin` 与 `onRegister` 各包一层 `try/catch`，捕获到异常时把对应状态从 `loading` 改成 `error`，并显示新的句子：登录是「登录没有成功。网络可能中断。留在此页再试。」，注册是「注册没有成功。网络可能中断。留在此页再试。」。两页都不加超时：表单提交由用户触发，挂起时用户能再点一次；只有进入文献库时自动发出的那一次读取需要超时，因为没有人会去点它。

组件测试里，超时用例让 `fetch` 桩返回一个监听 `init.signal` 的 Promise（收到 `abort` 就 reject），配合 `vi.useFakeTimers()` 与 `await vi.advanceTimersByTimeAsync(SESSION_TIMEOUT_MS)` 推进，外面包一层 `act`。抛错用例沿用 `App.test.tsx` 里已有的写法，让 `fetch` 桩 `throw new TypeError("network")`。

理由：`AbortController` 是浏览器原生机制，不引入依赖。导出常量让测试能推进假定时器而不必等真实的超时时长。

备选：(1) 把超时值做成组件 props 或 hook 参数以便测试注入 —— 否决，为测试改生产接口形状，`LibraryPage` 现在没有任何 props。(2) 包一个全局的带超时 `fetch` —— 否决，`Shell.tsx` 与上传、轮询都不需要超时，统一包装反而把不需要的行为塞进四条调用路径。

## Risks / Trade-offs

- 放宽规格后，「处理中」在真实时序下可能从不出现，操作者看不到这三个字 → `log` 的四条步骤仍然逐条出现，页面始终有内容；Scenario 与组件测试都改成断言当前状态加日志步骤，不再断言一个实现保证不了的文本。
- 机制级断言不等于真的执行了 `docker compose down -v`，卷删除本身没被 pytest 覆盖 → 端到端脚本 `tests/e2e_persistence_and_inspect.py` 继续在真实 Compose 上跑完整流程，`README.md`「测试」一节列了它；提交检查时两条路径都要过。
- `docker compose config` 的解析依赖 Compose 的输出格式，升级 Docker 后可能变 → 用例用 `--format json` 加标准库 `json` 解析而不是字符串匹配（也避免依赖 `backend/requirements.txt` 里没有的 PyYAML），格式变化时失败信息指向具体的键；断言只针对 `services.db.volumes` 与 `services.db.ports` 两个键。
- 假定时器与 `@testing-library/react` 的 `waitFor` 混用容易死锁 → 超时用例不使用 `waitFor`，改用 `act` 加 `advanceTimersByTimeAsync`，并在 `afterEach` 里 `vi.useRealTimers()`；其余用例继续用真实定时器。
- 给读取会话加超时后，慢网络下可能误判成错误状态 → `SESSION_TIMEOUT_MS` 取 10 秒，远大于本机与局域网的正常响应时间；错误句子已经写明下一步是刷新页面再试。
- 逐 Scenario 比对之后仍有五条不达标：`Open either entry` 与实现冲突，另外四条只由端到端脚本覆盖。本次不处理 → 用户已决定按例外记录，写进检查报告并另开变更；例外清单固定在 `tasks.md` 的 5.1 里，避免下次比对时又被当成新发现的缺口。

## Migration Plan

没有数据库迁移，没有接口变更，没有新的环境变量。改动集中在两份未归档变更的规格正文、两个前端页面和若干测试文件。部署方式不变，仍是 `README.md` 里的 `docker compose up --build`。回滚就是还原这些文件。

## Open Questions

- 无。
