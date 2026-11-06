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

## papers

一份已入库的文献。同一用户同一份内容只有一行。

| 列 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `uuid` | 文献标识 |
| `user_id` | `uuid` | 上传者，对应 `users.id` |
| `filename` | `text` | 上传时的文件名 |
| `content_sha256` | `text` | PDF 内容的 SHA-256，用于去重 |
| `created_at` | `timestamptz` | 入库时间 |

## chunks

文献的一个片段和它的向量。片段只在同一页内切出。

| 列 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `uuid` | 片段标识 |
| `paper_id` | `uuid` | 所属文献，对应 `papers.id` |
| `user_id` | `uuid` | 所属用户，对应 `users.id` |
| `page` | `integer` | 页码，从 1 起 |
| `content` | `text` | 片段正文，不超过 400 个字符 |
| `embedding` | `vector(2048)` | 片段的 2048 维向量 |
| `created_at` | `timestamptz` | 写入时间 |

## ingest_tasks

一次上传留下的处理任务。表充当队列，处理进程领取后更新状态和日志。

| 列 | 类型 | 含义 |
| --- | --- | --- |
| `id` | `uuid` | 任务标识 |
| `user_id` | `uuid` | 上传者，对应 `users.id` |
| `filename` | `text` | 上传时的文件名 |
| `content_sha256` | `text` | PDF 内容的 SHA-256，同一用户同一内容只有一条任务 |
| `pdf` | `bytea` | PDF 文件的原始字节 |
| `status` | `text` | 只使用「待处理」「处理中」「已可检索」「失败」 |
| `log` | `text[]` | 按顺序记录的处理步骤：「抽字」「切块」「嵌入」「写入」 |
| `paper_id` | `uuid` | 写入成功后的文献，对应 `papers.id`；未成功时为空 |
| `created_at` | `timestamptz` | 入队时间 |

## schema_migrations

迁移运行器记下已执行的版本。`version` 是 `text`，表示迁移文件名。
