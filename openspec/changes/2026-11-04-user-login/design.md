## Context

应用已经能启动，`/library` 和 `/reader` 谁都能打开。接口层在 `backend/app/api/`，业务层在 `services/`，数据访问在 `db/`。业务响应使用 `code`、`message`、`data`、`request_id`。见 `proposal.md` 的 Why，行为见 `specs/user-login/spec.md`。

## Goals / Non-Goals

**Goals:**

- 用户和会话落在现有分层里，口令只以 Argon2 哈希保存。
- 令牌是随机字符串，库存哈希，只在登录响应里出现一次。
- 前端把令牌放在 `localStorage`，刷新文献库后仍能认出当前用户。

**Non-Goals:**

- 不实现上传、检索、提问和退出登录。
- 不把令牌放进 URL 或 Cookie。

## Decisions

### 表

新增 `users` 与 `sessions`，只增、可回滚。

- `users`：`id`、`username`、`password_hash`、`created_at`。`username` 唯一。
- `sessions`：`id`、`user_id`、`token_hash`、`created_at`。`token_hash` 唯一。

备选是把明文令牌存在会话表里。哈希可以避免库备份直接变成可用令牌。

### 接口

`POST /api/v1/users` 和 `POST /api/v1/sessions` 不需要令牌。`GET /api/v1/sessions/current` 需要 `Authorization: Bearer`。这三项写进安全规范的授权清单，和 `GET /health` 并列。

重复用户名使用新错误码 `already_exists`，HTTP 409。先把这个码补进后端规范的错误码清单，再返回它。

用户名不存在和密码错误都走 `unauthenticated`。比较密码时即使用户不存在也做一次哈希运算，避免用响应时间区分这两种情况。

### 页面

`/login` 放注册和登录两个表单。登录成功后把令牌写入 `localStorage`，再导航到 `/library`。`/library` 和 `/reader` 在没有有效令牌时导航到 `/login`。文献库用 `GET /api/v1/sessions/current` 取用户名；还没有文献，所以正常结果就是空状态。

备选是登录成功后停在 `/login` 并只显示一句话。产品规则已经把登录成功后的页面定为文献库。

## Risks / Trade-offs

- [刷新后令牌还在 `localStorage`，同源脚本可以读到] → 本次不改用 Cookie。页面不把令牌写进 URL 或日志。
- [现有前端在未登录时仍会先画出文献库] → 路由在请求当前会话之前就转到 `/login`，不展示文献库内容。

## Migration Plan

增加一份只建 `users` 和 `sessions` 的迁移，并在 `docs/data-dictionary.md` 写下这两张表。回滚时按 `sessions`、`users` 的顺序删表。不改已有的 `vector` 扩展。
