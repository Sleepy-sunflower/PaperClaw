## Context

见 `proposal.md` 的 Why，行为见 `specs/paper-ingest/spec.md`。文献库现在只有空状态，没有上传控件。`papers`、`chunks` 和任务表还不存在。`db/init/01-vector.sql` 已创建 `vector` 扩展。`EMBEDDING_*` 已在 `.env.example` 和 `docker-compose.yml` 中，允许为空。还没有 `EMBEDDING_DIM`。接口层已经通过 `app.services.accounts` 访问用户和会话，不直接调用 `app.db`。

## Goals / Non-Goals

**Goals:**

- 上传请求在放入任务后马上返回，不调用嵌入接口。
- 处理进程与上传进程分开。停掉处理进程不丢失任务。
- 文献库用纯文本把状态和处理步骤打出来。

**Non-Goals:**

- 不做关键词检索、向量检索和阅读助手。
- 不提供原始 PDF 下载。处理完成后原文在片段里。
- 不实现删除文献。
- 不调用对话接口。`LLM_*` 保持可空。
- 不另加 Redis 或其他消息中间件。

## Decisions

### 数据库表充当队列

新增 `ingest_tasks`。上传进程插入一行，状态为「待处理」，并保存 PDF 字节、文件名、`user_id` 和文件内容的 SHA-256。处理进程用一条 `UPDATE ... WHERE status = '待处理'` 领取任务，改成「处理中」。没有领取到就说明别的进程已经拿走。

备选是在上传进程里起后台线程。不采用。停掉的是同一个进程，上传接口会一起停。

备选是 Redis。不采用。本机已经有 PostgreSQL，任务状态也要给页面读。

### 处理进程

Compose 增加 `worker`，使用和应用相同的镜像，命令为 `python -m app.worker`。它循环领取「待处理」的任务。领取后按顺序把「抽字」「切块」「嵌入」「写入」追加到该任务的文本日志里。抽字、切块和嵌入的规则与下面两节相同。全部成功后在一个事务里写入 `papers` 和 `chunks`，再把状态改为「已可检索」。任一步失败则状态改为「失败」，不留下可列出的文献。

进程恢复时重新领取仍为「待处理」的任务。已经「处理中」但进程中断的任务也重新做。写入前先按 `user_id` 和 SHA-256 查找：已有文献就不再插第二份，只把任务标成「已可检索」。

### 抽字与切块

用 `pypdf` 在内存中按页取文本，不把文件名拼进 shell。空白页跳过。全部页都抽不出正文时任务为「失败」，不写库。切块只在同一页内进行：窗口 400 个字符，步长 320。页长短于或等于 400 时整页为一块。更长时从 0 开始取窗口，尚未到页尾则起点加 320，最后一块可以短于 400。字符按 Python 字符串长度计算。片段保存页码，页码从 1 起。

备选是把全文连起来再切。不采用。那样一块会跨页，页码无法对应一个片段。

### 嵌入请求

地址是 `EMBEDDING_BASE_URL` 去掉末尾斜杠后接上 `/embeddings`。请求体只有 `model` 和 `input`。`input` 是这一块的正文。`model` 取 `EMBEDDING_MODEL`。`Authorization` 使用 `EMBEDDING_API_KEY`。不提交 `EMBEDDING_DIM`。只读取 `data[0].embedding`，长度必须等于 2048。一次只发送一块。

`EMBEDDING_DIM` 从环境变量读取。缺失、不是整数或不是 2048 时，处理进程把任务标为「失败」，不调用嵌入接口。列类型固定为 `vector(2048)`。上传进程启动仍不要求嵌入配置。`GET /health` 的行为不变。

密钥和片段正文不写入日志。响应和页面不包含 `EMBEDDING_API_KEY` 或 `LLM_API_KEY`。`.env.example` 只加键名 `EMBEDDING_DIM`。课程页面上的密钥只由操作者写进本机 `.env`，不进入仓库。

测试不访问真实嵌入接口。测试替换适配层的发送函数。成功路径的 PDF 不放进仓库：测试用 `pypdf` 在内存里写一页、正文长于 400 个字符的 PDF。

### 上传、幂等与授权

表单字段名为 `file`。先看大小，超过 20971520 字节直接 `invalid_argument`，不入库。再看文件头是否为 `%PDF`。文件名只保留最后一段，长度 1 至 200。空名或更长则 `invalid_argument`。

同一用户、同一 SHA-256 已有任务或已有文献时，不再插入第二份文献。上传仍返回 HTTP 202，`task_id` 指向已有的那次任务。

文献标识或任务标识不是 UUID 时返回 `invalid_argument`，不查库。是 UUID 时先取出记录，再核对 `user_id`。他人的文献与不存在的文献使用同一个 `not_found` 响应，比较时忽略各自的 `request_id`。任务也一样。

`papers` 列为 `id`、`user_id`、`filename`、`content_sha256`、`created_at`。`chunks` 列为 `id`、`paper_id`、`user_id`、`page`、`content`、`embedding`、`created_at`。`ingest_tasks` 列为 `id`、`user_id`、`filename`、`content_sha256`、`pdf`、`status`、`log`、`paper_id`、`created_at`。`status` 只使用「待处理」「处理中」「已可检索」「失败」。迁移文件为 `002_papers_chunks`，回滚先删 `ingest_tasks`，再删 `chunks`，再删 `papers`。

读取任务使用 `GET /api/v1/paper-tasks/{task_id}`。`data` 含 `task_id`、`status` 和 `log`。`log` 是按顺序排列的字符串。

安全规范的授权清单补上 `POST /api/v1/papers` 和 `GET /api/v1/paper-tasks/{task_id}`。列表和读取单份文献已经要求令牌。

`openspec/changes/2026-11-04-user-login/specs/user-login/spec.md` 仍写着文献库不得提供上传控件。实现时改掉那一句和对应 Scenario，使已登录的文献库可以上传。

### 文献库页面

`/library` 增加文件选择。上传时带当前令牌。返回 202 后轮询 `GET /api/v1/paper-tasks/{task_id}`，把 `status` 和 `log` 放进一个纯文本块，不做排版。状态为「已可检索」后拉取 `GET /api/v1/papers`，文件名作为文本节点显示。上传被拒绝或任务「失败」时留在文献库并显示错误。没有已可检索的文献时仍显示「还没有文献。」

## Risks / Trade-offs

- [处理进程中断后重做可能写出第二套片段] → 写入前按 `user_id` 和 `content_sha256` 查找，已有则不再插入。
- [测试若调用真实网关会消耗额度并接触密钥] → 测试替换适配层，不断言真实密钥的值。
- [20MB 的成功样本过大] → 边界只断言 20971521 字节被拒绝且不入队。成功路径使用测试在内存中生成的一页小 PDF。

## Migration Plan

向前迁移只新建 `papers`、`chunks` 和 `ingest_tasks`。已有 `users` 与 `sessions` 不动。回滚删除这三张新表，已有用户和会话仍在。部署时给本机 `.env` 补上 `EMBEDDING_DIM`，并让 Compose 把它传进应用和处理进程。不把值写进 `.env.example`。
