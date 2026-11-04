## Why

文献引路现在谁都能打开文献库和阅读助手，也没有用户记录。后面的文献必须属于上传者，所以要先能注册、登录，并在登录成功后进入文献库。

## What Changes

- 增加 `/login` 页面，同一页可以注册和登录。登录要有加载中和错误两种状态。
- 未登录打开 `/library` 或 `/reader` 时进入 `/login`。登录成功后进入 `/library`。
- 增加注册和登录接口。密码只存 Argon2 哈希。登录成功返回 Bearer 令牌，令牌不出现在 URL 里。
- 文献库在已登录且还没有文献时显示空状态，并显示当前用户名。本次不实现上传、检索和提问。

假设：没有注册就没有可登录的用户，因此本次包含注册。登录成功后的页面就是已有的文献库，不另做第三个内容页。

## Capabilities

### New Capabilities

- `user-login`: 个人研究者注册、登录、持有令牌后进入文献库；未登录不能停留在文献库或阅读助手。

### Modified Capabilities

- 无。`openspec/specs/` 里还没有已归档的能力规格。

## Impact

- 前端增加 `/login`，并改变 `/library`、`/reader` 在未登录时的去向。
- 后端新增用户表和会话表，以及 `POST /api/v1/users`、`POST /api/v1/sessions`、`GET /api/v1/sessions/current`。
- 安全规范里「只有 `GET /health` 不需要令牌」要补上注册和登录这两个公开接口。错误码清单要增加重复用户名。
- 不改伴随进程，不接入队列。
