## Purpose

让个人研究者注册并登录，登录成功后进入自己的文献库。未登录时不能停留在文献库或阅读助手。

## ADDED Requirements

### Requirement: Register with username and password

系统 SHALL 接受 `POST /api/v1/users`。用户名 MUST 为 1 至 32 个字符，只含小写字母、数字和连字符。密码 MUST 为 1 至 72 个字符。符合规则时 MUST 创建用户并返回 HTTP 201，响应含 `code` 为 `ok`、`message`、`data` 和 `request_id`。`data` MUST 含 `username`，MUST NOT 含密码或口令哈希。不符合规则时 MUST 返回 HTTP 400，`code` 为 `invalid_argument`。用户名已被占用时 MUST 返回 HTTP 409，`code` 为 `already_exists`，且不创建第二个用户。

#### Scenario: Register a new user

- **WHEN** 客户端向 `POST /api/v1/users` 提交用户名 `reader-one` 和 1 至 72 个字符的密码
- **THEN** 响应为 HTTP 201，`data.username` 为 `reader-one`，响应体没有密码

#### Scenario: Reject invalid registration

- **WHEN** 客户端提交空用户名、含大写字母的用户名，或空密码
- **THEN** 响应为 HTTP 400，`code` 为 `invalid_argument`，没有新用户

#### Scenario: Reject duplicate username

- **WHEN** 用户名 `reader-one` 已经存在，客户端再次用该用户名注册
- **THEN** 响应为 HTTP 409，`code` 为 `already_exists`，用户仍然只有一个

### Requirement: Login returns a bearer token

系统 SHALL 接受 `POST /api/v1/sessions`。用户名和密码都正确时 MUST 返回 HTTP 200，`data.token` 为令牌，`data.username` 为该用户。响应和 URL MUST NOT 包含密码或口令哈希。用户名不存在或密码不正确时 MUST 返回同一种 HTTP 401，`code` 为 `unauthenticated`，且两种响应体除 `request_id` 外一致。

#### Scenario: Login succeeds

- **WHEN** 已注册用户 `reader-one` 用正确密码调用 `POST /api/v1/sessions`
- **THEN** 响应为 HTTP 200，`data` 含 `token` 和 `username`，没有密码

#### Scenario: Wrong password matches unknown user

- **WHEN** 客户端用错误密码登录 `reader-one`，以及用任意密码登录不存在的用户名
- **THEN** 两次响应都是 HTTP 401，`code` 为 `unauthenticated`，除 `request_id` 外响应体一致

### Requirement: Current session requires the token

`GET /api/v1/sessions/current` MUST 只接受 `Authorization: Bearer <token>`。令牌有效时 MUST 返回 HTTP 200，`data.username` 为令牌对应用户。没有令牌或令牌无效时 MUST 返回 HTTP 401，`code` 为 `unauthenticated`，响应没有用户名。

#### Scenario: Read current user

- **WHEN** 客户端用刚登录得到的令牌调用 `GET /api/v1/sessions/current`
- **THEN** 响应为 HTTP 200，`data.username` 为登录时的用户名

#### Scenario: Reject missing or invalid token

- **WHEN** 客户端不带 `Authorization`，或带一个无效令牌调用 `GET /api/v1/sessions/current`
- **THEN** 响应为 HTTP 401，`code` 为 `unauthenticated`，响应体没有用户名

### Requirement: Login page and post-login library

`/login` SHALL 同时提供注册和登录，并写出用户名和密码的规则。这一页 MUST NOT 显示大标题「文献引路」，也 MUST NOT 显示文献库或阅读助手菜单。提交过程中 MUST 显示加载中。失败时 MUST 显示错误，并写明发生了什么、可能的原因、下一步。注册或登录的请求抛出异常时 MUST 显示错误状态，MUST NOT 一直显示加载中。登录成功后 MUST 进入 `/library`，此时页面 MUST 显示大标题和两个菜单。已登录且没有文献时，文献库 MUST 显示空状态和当前用户名。文献库首次读取 `GET /api/v1/sessions/current` MUST 有超时；该请求抛出异常或超时 MUST 显示错误状态，MUST NOT 一直显示加载中。未登录打开 `/`、`/library` 或 `/reader` 时 MUST 进入 `/login`，并且仍然不显示大标题和菜单。`GET /health`、`POST /api/v1/users` 和 `POST /api/v1/sessions` 以外的业务接口，没有有效令牌时 MUST 拒绝。

#### Scenario: Successful login opens the library

- **WHEN** 访问者在 `/login` 用正确的用户名和密码登录
- **THEN** 浏览器地址变为 `/library`，页面显示该用户名和空状态

#### Scenario: Login failure stays on the page

- **WHEN** 访问者在 `/login` 提交错误密码
- **THEN** 页面仍在 `/login`，显示错误，并说明可以重新输入

#### Scenario: Login page shows an error when the request fails

- **WHEN** 访问者在 `/login` 提交注册或登录，而请求因为网络中断抛出异常
- **THEN** 页面仍在 `/login`，显示对应的错误句子并写明下一步，不再显示「正在注册。」或「正在登录。」

#### Scenario: Library shows an error when the session read times out

- **WHEN** 已登录的访问者打开 `/library`，而读取 `GET /api/v1/sessions/current` 的请求超时或抛出异常
- **THEN** 页面显示错误状态并写明下一步，不再显示「正在读取你的文献。」

#### Scenario: Unauthenticated pages go to login

- **WHEN** 未登录的访问者打开 `/`、`/library` 或 `/reader`
- **THEN** 浏览器地址变为 `/login`
