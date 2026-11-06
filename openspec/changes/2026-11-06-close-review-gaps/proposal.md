## Why

另一位审查者对着规则和规格逐条核对，找出三处确实存在的缺口。第一，`paper-ingest` 要求文献库页面文本里出现「待处理」「处理中」「已可检索」，但页面只在轮询观察到状态变化时追加，处理进程在两次轮询之间跑完时「处理中」永远不会出现，服务端也不保存状态历史，页面补不出来。第二，`data-persistence`、`db-inspection` 和 `paper-ingest` 里有七个 Scenario 只被端到端驱动脚本覆盖或完全没有覆盖，与 `4-testing.mdc`「每个 Scenario 至少对应一个 `test_` 用例」不符。第三，登录和注册的 `fetch` 没有捕获异常，文献库读取当前会话没有超时，网络失败时页面永远停在「正在登录。」「正在注册。」「正在读取你的文献。」，违反 `1-product.mdc` 的视图状态判据。

## What Changes

- **BREAKING**（对规格而言，对用户不是）：放宽 `paper-ingest` 的 Requirement `Library prints the task and lists only ready papers`。页面 MUST 显示任务的当前状态和日志步骤，MUST NOT 因为轮询跳过中间状态而停在旧状态或留白；不再要求三种状态都必须在页面上出现过。相应改写 Scenario `Library shows the task log`，新增 Scenario `Skipped intermediate status does not stall the page` 作为「跳过中间状态」这条用例的来源，并改写它们的组件测试。
- 给七个没有 `test_` 用例的 Scenario 补上用例：`data-persistence` 的 `Restart does not re-run applied migrations`、`down -v clears the data`、`git status stays clean`、`Database port is not reachable from the host`，`db-inspection` 的 `Empty database`、`Stack is stopped`，`paper-ingest` 的 `List hides other users' papers`。每条用例在 docstring 里写明 Scenario 名称。
- 扩充 `user-login` 的 Requirement `Login page and post-login library`：提交过程中请求抛错或超时 MUST 显示错误状态，MUST NOT 一直显示加载中；文献库首次读取当前会话 MUST 有超时，抛错或超时 MUST 显示错误状态。补两个 Scenario，并用组件测试覆盖。
- 按上述规格改 `frontend/src/pages/LoginPage.tsx` 和 `frontend/src/pages/LibraryPage.tsx`：三个 `fetch` 加 `try/catch`，读取当前会话加 `AbortController` 超时。错误句子按 `1-product.mdc` 写出发生了什么、可能的原因、下一步。
- 后端接口、数据库结构、`tools/db_inspect.py` 的行为和 Compose 编排都不改。
- 比对时另外发现五条 Scenario 仍然只由 `tests/e2e_*.py` 覆盖或规格已过时：`runtime-skeleton` 的 `Open either entry`（文献库现在有上传表单，这条与实现冲突）、`data-persistence` 的 `Registered user and paper survive down and up`、`db-inspection` 的 `Inspect after registering and uploading`、`No credentials in the output`、`Data unchanged after inspection`。按用户决定，本次不改也不补用例，作为例外记进检查报告，另开变更处理。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- 无。`openspec list --specs` 没有已归档规格，要改的两条 Requirement 只写在未归档变更 `2026-11-04-paper-ingest` 和 `2026-11-04-user-login` 里。沿用变更 `2026-11-04-align-session-checks` 的做法：本变更设置 `skip_specs: true`，规格正文的修改直接记在那两个变更的 `specs/paper-ingest/spec.md` 和 `specs/user-login/spec.md`，不另写一份会与之冲突的 capability。

## Impact

- `openspec/changes/2026-11-04-paper-ingest/specs/paper-ingest/spec.md`：Requirement `Library prints the task and lists only ready papers` 与 Scenario `Library shows the task log` 改写，新增 Scenario `Skipped intermediate status does not stall the page`。
- `openspec/changes/2026-11-04-user-login/specs/user-login/spec.md`：Requirement `Login page and post-login library` 扩充，新增两个 Scenario。
- `frontend/src/pages/LoginPage.tsx`：`onLogin` 与 `onRegister` 捕获异常并切到错误状态，新增两句错误文案。
- `frontend/src/pages/LibraryPage.tsx`：读取 `GET /api/v1/sessions/current` 的请求带超时，抛错或超时切到已有的错误状态。
- `frontend/src/pages/LibraryPage.test.tsx`：Scenario `Library shows the task log` 的断言改成当前状态加日志步骤。
- `frontend/src/App.test.tsx`：新增登录、注册请求抛错和文献库读取会话超时三条组件测试。
- `tests/normal/`：新增迁移幂等、`docker compose config` 的数据卷与端口断言、`tools/db_inspect.py` 空库报告三条用例。
- `tests/failure/`：`test_paper_ingest_failures.py` 补上用户 B 的列表为空的断言；新增清空数据后旧凭证登录被拒、`tools/db_inspect.py` 停栈退出码非 0 两条用例。
- `README.md` 与 `docs/data-dictionary.md` 不需要改：接口路径、状态码、表和字段都没有变。
