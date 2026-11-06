## Purpose

让已登录的个人研究者上传自己的 PDF。上传马上返回，另一个进程切块并写入向量。文献库用纯文本显示做到哪一步，并且只列出这个用户已可检索的文献。

## ADDED Requirements

### Requirement: Upload enqueues processing

系统 SHALL 接受 `POST /api/v1/papers`。请求 MUST 带 `Authorization: Bearer <token>`。正文是一份 PDF，大小不超过 20971520 字节。令牌有效且文件头是 PDF 时，这次请求 MUST NOT 调用嵌入接口。系统 MUST 留下文件、放入任务，并返回 HTTP 202，`code` 为 `ok`，`data` 含 `task_id`，状态为「待处理」。响应 MUST NOT 包含片段原文、向量、`EMBEDDING_API_KEY` 或 `LLM_API_KEY`。

#### Scenario: Upload returns before embedding

- **WHEN** 已登录用户上传一份不超过 20971520 字节、文件头为 PDF 的文件
- **THEN** 响应为 HTTP 202，`code` 为 `ok`，`data` 含 `task_id` 且状态为「待处理」，响应里没有片段原文和向量

### Requirement: A separate process stores chunks and vectors

处理进程 MUST 与接受上传的进程分开。它取到任务后 MUST 把状态改为「处理中」，并依次记录「抽字」「切块」「嵌入」「写入」。抽字按页进行。每一页内以 400 个字符为窗口、80 个字符重叠切块。嵌入请求只提交模型和文本，MUST NOT 提交维度。每个向量长度 MUST 为 2048。写完后状态 MUST 为「已可检索」，文献和片段属于上传者。片段 MUST 记有页码，每个片段正文不超过 400 个字符，同一页上相邻片段重叠 80 个字符。停掉处理进程后再上传，上传 MUST 仍返回 HTTP 202，任务保持「待处理」。处理进程恢复后 MUST 继续做完，用户不必再传一次。同一文件内容再次上传，或同一条任务被处理两次，MUST 只留下一份文献和一套片段。

#### Scenario: Stored chunks belong to the uploader

- **WHEN** 处理进程做完一份至少一页、且该页正文长于 400 个字符的 PDF
- **THEN** 该用户名下有一条文献和至少一个片段，状态为「已可检索」，片段记有页码，每个片段正文不超过 400 个字符，同一页上相邻片段重叠 80 个字符，每个向量长度为 2048

#### Scenario: Stopped worker keeps the task

- **WHEN** 处理进程已停，已登录用户上传一份文件头为 PDF 的文件
- **THEN** 响应为 HTTP 202，任务状态为「待处理」；处理进程恢复后该任务变为「已可检索」，且用户没有再次上传

#### Scenario: Duplicate upload stores one paper

- **WHEN** 已登录用户把同一份 PDF 的内容再上传一次
- **THEN** 该用户名下只有一份文献和一套片段

### Requirement: Library prints the task and lists only ready papers

系统 SHALL 接受读取任务状态的请求，且 MUST 带当前用户的 Bearer 令牌。文献库页面 MUST 以纯文本显示「待处理」「处理中」「已可检索」「失败」，以及处理过程中的「抽字」「切块」「嵌入」「写入」。状态成为「已可检索」后，页面 MUST 以文本显示该文件名，并且不再显示「还没有文献。」文件名中的引号和 HTML 标签 MUST 按字面显示。`GET /api/v1/papers` MUST 只返回该用户状态已是「已可检索」的文献标识和文件名，MUST NOT 含片段原文、向量或其他用户的文件名。还没有已可检索的文献时，`data` MUST 为空数组。

#### Scenario: Library shows the task log

- **WHEN** 已登录用户在 `/library` 上传一份 PDF，并且处理进程做完
- **THEN** 页面文本里出现「待处理」「处理中」「已可检索」「抽字」「切块」「嵌入」「写入」

#### Scenario: Library shows the uploaded filename

- **WHEN** 该任务的状态已成为「已可检索」
- **THEN** 文献库页面显示该文件名，并且不显示「还没有文献。」

#### Scenario: Filename is shown as text

- **WHEN** 已登录用户上传的 PDF 文件名含有引号和 HTML 标签，且任务已成为「已可检索」
- **THEN** 文献库页面原样显示这些字符，不把它们当作 HTML

### Requirement: Papers and tasks stay private

系统 SHALL 接受 `GET /api/v1/papers/{paper_id}`。请求 MUST 带当前用户的 Bearer 令牌。文献属于该用户且已可检索时 MUST 返回 HTTP 200，`code` 为 `ok`，`data` 含标识和文件名，且 MUST NOT 含片段原文或向量。文献属于其他用户，或标识不存在时，MUST 返回 HTTP 404，`code` 为 `not_found`。这两种响应的 `code`、`message` 和 `data` MUST 相同，且 MUST NOT 含对方的文件名、页码或原文片段。他人的任务与不存在的任务同样返回 `not_found`。没有令牌或令牌无效时，上传、列表、读取单份文献和读取任务 MUST 返回 HTTP 401，`code` 为 `unauthenticated`，响应里没有文件名或正文。

#### Scenario: Another user cannot read the paper

- **WHEN** 用户 A 的令牌把路径中的文献标识换成用户 B 的文献标识
- **THEN** 响应与请求一个不存在的标识相同，为 HTTP 404，`code` 为 `not_found`，且不含用户 B 的文件名、页码和原文

#### Scenario: List hides other users' papers

- **WHEN** 用户 A 的一份 PDF 已可检索，用户 B 调用 `GET /api/v1/papers`
- **THEN** 响应为 HTTP 200，`data` 里没有用户 A 的文件名

#### Scenario: Missing token is rejected

- **WHEN** 客户端不带 `Authorization` 调用 `GET /api/v1/papers`
- **THEN** 响应为 HTTP 401，`code` 为 `unauthenticated`，且没有文件名或正文

### Requirement: Invalid uploads and failed processing store nothing listable

不是 PDF，或文件大于 20971520 字节时，上传 MUST 返回 HTTP 400，`code` 为 `invalid_argument`，并且 MUST NOT 放入任务。抽不出正文、嵌入配置缺失、嵌入接口失败，或向量长度不是 2048 时，任务 MUST 变为「失败」，并且 MUST NOT 留下可被 `GET /api/v1/papers` 列出的文献。这些响应 MUST NOT 包含 `EMBEDDING_API_KEY` 或 `LLM_API_KEY`。空的嵌入配置 MUST NOT 阻止上传进程启动，也 MUST NOT 改变 `GET /health` 在数据库连通时返回 HTTP 200。

#### Scenario: Reject a non-PDF

- **WHEN** 已登录用户上传的文件不是 PDF
- **THEN** 响应为 HTTP 400，`code` 为 `invalid_argument`，随后 `GET /api/v1/papers` 的 `data` 仍为空数组

#### Scenario: Embedding failure stores nothing

- **WHEN** 已登录用户上传一份文件头为 PDF 的文件，而处理时嵌入接口失败或返回的向量长度不是 2048
- **THEN** 上传响应曾为 HTTP 202，随后任务状态为「失败」，该用户的文献列表仍为空
