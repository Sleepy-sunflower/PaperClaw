# 数据字典

## users

个人研究者的账号。

| 列 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `uuid` | 用户标识 |
| `username` | `text` | 登录用户名，全库唯一 |
| `password_hash` | `text` | 口令的 Argon2 哈希，不是口令本身 |
| `created_at` | `timestamptz` | 注册时间 |

## sessions

一次登录发出的令牌。表里只存令牌哈希。

| 列 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `uuid` | 会话标识 |
| `user_id` | `uuid` | 令牌所属用户，对应 `users.id` |
| `token_hash` | `text` | 令牌的 SHA-256 哈希，全库唯一 |
| `created_at` | `timestamptz` | 登录时间 |

## schema_migrations

迁移运行器记下已执行的版本。`version` 是 `text`，表示迁移文件名。
