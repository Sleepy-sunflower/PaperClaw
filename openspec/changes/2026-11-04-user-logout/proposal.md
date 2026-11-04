## Why

登录后令牌一直留在浏览器里，关掉浏览器再打开仍然是登录状态。用户需要一个明确的动作结束这次登录，并让这枚令牌不能再使用。

## What Changes

- 在登录后的外壳上增加「登出」。文献库和阅读助手都能看到。登录页没有这个按钮。
- `DELETE /api/v1/sessions/current` 需要 Bearer 令牌。成功时删除服务端这条会话，返回 HTTP 200。
- 浏览器删掉本地保存的令牌，并进入 `/login`。之后用这枚旧令牌访问 `GET /api/v1/sessions/current` 必须得到 HTTP 401。
- 没有令牌或令牌无效时，登出返回 HTTP 401，`code` 为 `unauthenticated`。

本次不改变令牌的保存位置。关掉浏览器仍会保留登录，直到用户点击登出。

## Capabilities

### New Capabilities

- `user-logout`: 已登录用户从外壳登出，服务端会话作废，浏览器回到登录页。

### Modified Capabilities

- 无。`openspec/specs/` 里还没有已归档的能力规格。登录行为仍在变更 `2026-11-04-user-login` 中。

## Impact

- 前端外壳增加登出按钮。`frontend/src/auth.ts` 增加清除令牌。
- 后端 `sessions` 增加删除当前会话。不改用户表。
- 安全规范的授权清单要写明这个接口必须带令牌。
