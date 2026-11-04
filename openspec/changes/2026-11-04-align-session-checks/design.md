## Context

见 `proposal.md` 的 Why。当前 `backend/app/api/users.py` 直接调用 `insert_user`。`backend/app/api/sessions.py` 直接调用 `find_user`、`insert_session`、`find_username_by_token_hash` 和 `delete_session_by_token_hash`。SQL 在 `backend/app/db/users.py`。口令哈希在 `backend/app/services/passwords.py`。健康检查已经是接口层调用 `app.services.health`。

`tests/normal/test_user_logout.py` 里的 `test_logout_without_a_token` 覆盖 Scenario `Logout without a token`。`frontend/src/Shell.tsx` 在登出响应为 200 或 401 时清除 `paperclaw.token` 并进入 `/login`；其他状态或 `fetch` 抛错时留在原页。`openspec/changes/2026-11-04-user-logout/design.md` 已写明这一点。同目录 `specs/user-logout/spec.md` 的 Requirement `Logout control is on the shell` 没有写这个例外。

## Goals / Non-Goals

**Goals:**

- 接口层不再引用 `app.db`。注册和三个会话接口都经业务层访问数据库。
- 失败 Scenario 的用例位于 `tests/failure/`。
- 未归档的登出规格与现有页面行为使用同一套点击结果。

**Non-Goals:**

- 不改接口路径、状态码、错误码和响应字段。
- 不改 `Shell.tsx` 的登出分支。成功点击仍清除令牌并进入 `/login`。
- 不放宽 `.cursor/rules/2-backend.mdc` 或 `.cursor/rules/4-testing.mdc`。
- 不改表，也不把令牌从 `localStorage` 改成 `sessionStorage`。

## Decisions

### 业务层承接现有的数据库调用

新增 `backend/app/services/accounts.py`。注册、登录、读取当前会话和登出各自经这里的函数访问 `app.db.users`。口令哈希仍由 `app.services.passwords` 完成，并由这些业务函数调用。业务函数向接口层返回可区分的结果（成功、用户名已存在、未登录）。接口层只把结果写成现有的 `code` 和 HTTP 状态，不 import `app.db`，也不捕获数据库驱动的异常来判断业务结果。业务层不 import `app.api`，不返回 `JSONResponse`。

范围包括注册和全部会话接口。只给登出包一层会留下登录、读取当前会话和注册继续直接调用数据访问层。

备选是改 `2-backend.mdc`，允许会话接口直接调用数据访问层。不采用。这次要让代码符合已有规则。

备选是把 SQL 搬进业务层。不采用。规则要求业务层不写 SQL。

### 失败用例只移动位置

新建 `tests/failure/test_user_logout_failures.py`，放入 `test_logout_without_a_token`。文档字符串仍是 `Scenario: Logout without a token`。断言仍是 HTTP 401，`code` 为 `unauthenticated`。该文件自备测试客户端和清库，不从 `tests/normal/` 导入测试模块。`tests/normal/test_user_logout.py` 只保留 `test_logout_succeeds`。

### 规格改成与页面一致

改 `openspec/changes/2026-11-04-user-logout/specs/user-logout/spec.md` 里 Requirement `Logout control is on the shell` 的正文为：

登录后的文献库和阅读助手 MUST 显示「登出」。点击后 MUST 先调用 `DELETE /api/v1/sessions/current`。响应为 HTTP 200 或 HTTP 401 时，MUST 清除浏览器里保存的令牌，并进入 `/login`。请求没有得到响应，或响应不是这两个状态时，MUST 留在原页，显示「登出没有成功。网络可能中断。留在此页再试。」，并且 MUST NOT 清除令牌。`/login` MUST NOT 显示「登出」。登出完成后再打开 `/library` 或 `/reader`，MUST 进入 `/login`，并且不显示大标题和菜单。

保留 Scenario `Click logout from the library` 和 `Login page has no logout`。追加：

#### Scenario: Logout stays when the request fails

- **WHEN** 已登录用户在 `/library` 点击「登出」，而登出请求没有得到响应，或响应不是 HTTP 200 也不是 HTTP 401
- **THEN** 地址仍是 `/library`，页面显示「登出没有成功。网络可能中断。留在此页再试。」，`paperclaw.token` 仍在

`frontend/src/App.test.tsx` 为这个 Scenario 增加组件测试。`fetch` 抛错和 HTTP 500 都要断言留在 `/library` 且令牌仍在。不改 `Shell.tsx`。

备选是改页面，让任何点击都清除令牌并进入 `/login`。不采用。那样会在请求没有到达时清掉仍然有效的令牌，也和已有 `design.md` 相反。

## Risks / Trade-offs

- [搬动调用时改了响应] → 现有注册、登录、会话和登出用例的断言保持不变，搬完后这些用例必须通过。
- [失败用例被收集两次] → 从 `tests/normal/test_user_logout.py` 删除 `test_logout_without_a_token`，只在 `tests/failure/` 保留一份。
- [规格句子和页面文案不一致] → 错误句使用 `Shell.tsx` 里的原文。

## Migration Plan

不改表，也不改环境变量。回滚时恢复接口层对 `app.db.users` 的直接调用，并把规格正文改回原句。已有会话继续有效。
