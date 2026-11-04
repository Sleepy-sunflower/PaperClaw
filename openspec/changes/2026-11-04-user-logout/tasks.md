## 1. Logout API

- [x] 1.1 在安全规范的授权清单写明 `DELETE /api/v1/sessions/current` 必须带 Bearer 令牌。核对 `3-security.mdc` 已包含这句。
- [x] 1.2 按 `token_hash` 删除当前会话。用 pytest 覆盖 `user-logout` 规格中的两个接口 Scenario：登出成功后旧令牌不能再读当前用户；不带令牌登出返回 HTTP 401。测试使用单独的数据库。

## 2. Logout control

- [x] 2.1 在登录后的外壳增加「登出」。点击后调用 `DELETE /api/v1/sessions/current`，成功则清除 `localStorage` 的 `paperclaw.token` 并进入 `/login`。`/login` 不显示「登出」。用组件测试覆盖规格中的两个页面 Scenario。文献库或阅读助手收到当前会话 HTTP 401 时，也清除令牌并进入 `/login`。
