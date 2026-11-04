## Purpose

让已登录的个人研究者主动结束这次登录。登出后旧令牌不能再使用，页面回到登录页。

## ADDED Requirements

### Requirement: Logout deletes the current session

系统 SHALL 接受 `DELETE /api/v1/sessions/current`。请求 MUST 带 `Authorization: Bearer <token>`。令牌有效时 MUST 删除该令牌对应的会话，返回 HTTP 200，`code` 为 `ok`，`data` 为 `null`。响应 MUST NOT 包含令牌或口令。没有令牌或令牌无效时 MUST 返回 HTTP 401，`code` 为 `unauthenticated`。同一枚令牌再次登出 MUST 得到 HTTP 401。

#### Scenario: Logout succeeds

- **WHEN** 已登录用户用当前令牌调用 `DELETE /api/v1/sessions/current`
- **THEN** 响应为 HTTP 200，`code` 为 `ok`，随后用这枚令牌调用 `GET /api/v1/sessions/current` 得到 HTTP 401

#### Scenario: Logout without a token

- **WHEN** 客户端不带 `Authorization` 调用 `DELETE /api/v1/sessions/current`
- **THEN** 响应为 HTTP 401，`code` 为 `unauthenticated`

### Requirement: Logout control is on the shell

登录后的文献库和阅读助手 MUST 显示「登出」。点击后 MUST 先调用登出接口，再清除浏览器里保存的令牌，并进入 `/login`。`/login` MUST NOT 显示「登出」。登出完成后再打开 `/library` 或 `/reader`，MUST 进入 `/login`，并且不显示大标题和菜单。

#### Scenario: Click logout from the library

- **WHEN** 已登录用户在 `/library` 点击「登出」
- **THEN** 浏览器地址变为 `/login`，页面没有大标题「文献引路」，也没有文献库和阅读助手菜单

#### Scenario: Login page has no logout

- **WHEN** 访问者打开 `/login`
- **THEN** 页面没有「登出」
