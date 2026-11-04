## 1. Account service

- [x] 1.1 新增 `backend/app/services/accounts.py`，让注册、登录、读取当前会话和登出经它访问 `app.db.users`。接口层只把业务结果写成现有的 `code` 和 HTTP 状态。验证：`backend/app/api/users.py` 与 `backend/app/api/sessions.py` 不再出现 `app.db`；`backend/app/services/accounts.py` 不引用 `app.api`；`pytest tests/normal/test_user_api.py tests/failure/test_user_api_failures.py tests/normal/test_user_logout.py` 退出码为 0，且这些文件里的断言没有改。

## 2. Failure test location

- [x] 2.1 把 `test_logout_without_a_token` 移到 `tests/failure/test_user_logout_failures.py`，从 `tests/normal/test_user_logout.py` 删除。新文件自备测试客户端，文档字符串仍为 `Scenario: Logout without a token`。验证：`pytest tests/failure/test_user_logout_failures.py tests/normal/test_user_logout.py` 退出码为 0；正常路径文件不再包含 `test_logout_without_a_token`；失败用例仍断言 HTTP 401 且 `code` 为 `unauthenticated`。

## 3. Logout spec alignment

- [x] 3.1 按 `design.md` 改写 `openspec/changes/2026-11-04-user-logout/specs/user-logout/spec.md` 中 Requirement `Logout control is on the shell`，并追加 Scenario `Logout stays when the request fails`。验证：该 Requirement 写明 HTTP 200 或 HTTP 401 时清除令牌并进入 `/login`，其他情况留在原页且 MUST NOT 清除令牌；Scenario `Click logout from the library` 与 `Login page has no logout` 仍在。

- [x] 3.2 在 `frontend/src/App.test.tsx` 为 Scenario `Logout stays when the request fails` 增加组件测试，分别覆盖 `fetch` 抛错和 HTTP 500。验证：在 `frontend/` 执行 `npm test`，退出码为 0；`frontend/src/Shell.tsx` 的登出分支没有改动。
