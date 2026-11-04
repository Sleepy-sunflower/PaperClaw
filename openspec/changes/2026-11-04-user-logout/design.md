## Context

令牌存在浏览器 `localStorage` 的 `paperclaw.token`。服务端 `sessions` 表只存 `token_hash`。登录后的外壳在 `frontend/src/Shell.tsx`，大标题和菜单只在这里。见 `proposal.md` 的 Why。行为见 `specs/user-logout/spec.md`。

## Goals / Non-Goals

**Goals:**

- 登出同时删掉服务端会话和浏览器里的令牌。
- 按钮只出现在登录后的外壳上。

**Non-Goals:**

- 不把令牌从 `localStorage` 改成 `sessionStorage`。关掉浏览器仍会保留登录。
- 不实现「退出全部设备」。只作废当前这枚令牌。

## Decisions

### 接口

使用 `DELETE /api/v1/sessions/current`，与现有 `GET /api/v1/sessions/current` 是同一资源。按令牌哈希删除对应行。不在路径里放动词。

备选是 `POST /api/v1/sessions/logout`。路径里的 `logout` 是动词，和后端规范不一致。

没有令牌或哈希对不上时返回 `unauthenticated`。不把「已经登出」说成成功，避免别人用响应判断令牌是否曾经有效。

### 页面

外壳导航在两个菜单下面增加「登出」。点击后调用删除接口，无论接口成功还是 401，都清除 `localStorage` 并进入 `/login`。网络失败时留在原页并显示错误，不清除令牌，避免用户以为已经登出但令牌仍有效。

## Risks / Trade-offs

- [接口成功但清除本地令牌之前页面被关掉] → 服务端会话已经删除，旧令牌不能再用。用户下次打开会因 401 回到登录页。当前实现里文献库只在启动时请求当前会话；这次要在 401 时清除令牌并进入 `/login`。

## Migration Plan

不改表。回滚时去掉登出路由和按钮即可，已有会话继续有效。
