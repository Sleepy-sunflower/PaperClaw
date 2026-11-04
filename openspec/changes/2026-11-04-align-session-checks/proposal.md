## Why

登出相关的规则、规格和代码各说各的。分层规则要求接口层不直接调用数据访问层，注册和会话接口却直接调用。失败路径应放在 `tests/failure/`，不带令牌登出的用例却在 `tests/normal/`。规格要求点击登出后一定清除令牌并进入登录页，设计和页面在网络失败时留在原页。

## What Changes

- 注册、登录、读取当前会话和登出改为经业务层访问数据库。SQL 仍留在数据访问层。这四个接口的路径、状态码和响应体不变。
- 把 Scenario `Logout without a token` 的用例移到 `tests/failure/`。断言仍是 HTTP 401，`code` 为 `unauthenticated`。
- 改写未归档变更 `2026-11-04-user-logout` 的规格，使点击登出与 `design.md` 和 `frontend/src/Shell.tsx` 一致：接口返回 200 或 401 时清除令牌并进入 `/login`；网络失败或其他状态时留在原页，显示「登出没有成功。网络可能中断。留在此页再试。」，不清除令牌。补上这个 Scenario，并用组件测试覆盖。成功登出的页面行为不变。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- 无。`openspec list --specs` 没有已归档规格。登出需求只写在变更 `2026-11-04-user-logout` 里。运行中的行为不变，所以本变更设置 `skip_specs: true`，不另写一份 capability。规格正文的修改记在该变更的 `specs/user-logout/spec.md`。

## Impact

- `backend/app/api/users.py` 与 `backend/app/api/sessions.py` 不再引用 `app.db`。
- 业务层新增函数，由上述接口调用。`backend/app/db/users.py` 继续负责 SQL。
- `tests/normal/test_user_logout.py` 只保留成功用例。失败用例改到 `tests/failure/`。
- `openspec/changes/2026-11-04-user-logout/specs/user-logout/spec.md` 的登出按钮 Requirement，以及 `frontend/src/App.test.tsx` 增加网络失败场景。
