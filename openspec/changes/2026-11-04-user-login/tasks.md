## 1. Schema

- [x] 1.1 新增只建 `users` 和 `sessions` 的迁移，字段按 `design.md`。回滚先删 `sessions` 再删 `users`。执行迁移再回滚，确认两张表消失且 `vector` 扩展仍在。
- [x] 1.2 在 `docs/data-dictionary.md` 写下这两张表的列名、类型和含义。对照迁移文件，确认没有遗漏列。

## 2. Auth API

- [x] 2.1 在后端错误码清单加入 `already_exists` / HTTP 409，并在安全规范的授权清单写明 `POST /api/v1/users` 与 `POST /api/v1/sessions` 不需要令牌。核对两份规范文件已包含这两句。
- [x] 2.2 实现注册、登录和当前会话三个接口，口令用 Argon2 哈希，令牌只存哈希。用 pytest 覆盖 `user-login` 规格中的接口 Scenario：注册成功、参数非法、用户名重复、登录成功、错误密码与不存在用户的响应一致、当前会话成功、缺令牌或令牌无效。测试使用单独的数据库。

## 3. Login page

- [x] 3.1 增加 `/login`，同一页可注册和登录，提交时显示加载中，失败时显示含原因和下一步的错误。登录成功后把令牌写入 `localStorage` 并进入 `/library`。未登录打开 `/library` 或 `/reader` 时进入 `/login`。已登录的文献库显示用户名和空状态，没有上传控件。用组件测试覆盖规格中的三个页面 Scenario。
