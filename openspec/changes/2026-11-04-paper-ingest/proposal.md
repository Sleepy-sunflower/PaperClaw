## Why

登录已经能演示，文献库仍然是空的。抽正文、切块和写入向量可能要几十秒，不能占着同一次上传请求。上传应马上返回，由另一个进程做完，并让用户在文献库里看到做到哪一步。

## What Changes

- 已登录用户在文献库上传一份 PDF。上传只确认这是当前用户的 PDF、把文件留下、放入任务，然后返回 HTTP 202 和 `task_id`。
- 另一个进程从任务里取工作：按页抽出正文，以 400 字为窗口、80 字重叠切块，调用嵌入接口得到 2048 维向量，记在当前用户名下。
- 文献库用纯文本显示任务状态：待处理、处理中、已可检索、失败，以及抽字、切块、嵌入、写入。已可检索后列出文件名。另一名用户看不到这份文献。
- 同一份 PDF 再次上传，或同一条任务被处理两次，只留下一份文献和一套片段。
- 嵌入地址、密钥、模型名和维度只从环境变量读取。`.env.example` 只增加键名 `EMBEDDING_DIM`，不写值。密钥不出现在页面、接口响应和日志里。
- 检索和阅读助手不在这次。

## Capabilities

### New Capabilities

- `paper-ingest`: 登录后上传 PDF，异步切块并写入向量；文献库打印任务状态，并只列出当前用户已可检索的文献。

### Modified Capabilities

- 无。`openspec list --specs` 没有已归档规格。

## Impact

- `POST /api/v1/papers` 返回 HTTP 202。新增读取任务状态的接口。`GET /api/v1/papers` 和 `GET /api/v1/papers/{paper_id}` 仍要带当前用户的 Bearer 令牌。
- 数据库新增 `papers`、`chunks` 和 `ingest_tasks`。`docs/data-dictionary.md` 要补上这些表。
- Docker Compose 增加一个处理进程，与接受上传的进程分开。
- 文献库页面增加上传，并用纯文本打印任务过程。
- `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`、`EMBEDDING_DIM` 从本机 `.env` 进入处理进程。空的嵌入配置仍允许上传进程启动；处理时缺少这些配置则任务失败，不留下可列出的文献。
