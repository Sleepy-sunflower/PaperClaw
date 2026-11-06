## Purpose

描述操作者查看数据库内容的命令：在仓库根目录执行一条命令，就能看到库里的用户、文献、入库任务和片段正文摘要，输出里不出现凭证、口令和向量数值。

## ADDED Requirements

### Requirement: One command shows users and paper content

仓库 SHALL 提供一条在根目录执行的命令，显示当前 Compose 栈数据库里的内容。输出 MUST 分节列出：用户（用户名与创建时间）、会话（所属用户与创建时间，或其条数）、文献（文件名、所属用户、片段数）、入库任务（文件名、状态、日志）和片段（页码与正文摘要）。命令 MUST NOT 要求操作者手动进容器或手写 SQL。命令 SHALL 支持指定 Compose 项目名和环境变量文件，默认使用根目录的日常栈。

#### Scenario: Inspect after registering and uploading

- **WHEN** 操作者注册一个用户、上传一份 PDF 并等到任务变为「已可检索」，然后运行该命令
- **THEN** 输出里能看到该用户名、该文件名、该任务的状态「已可检索」，以及该文献片段的正文摘要，摘要里包含 PDF 中的文字

#### Scenario: Empty database

- **WHEN** 数据库是空的，操作者运行该命令
- **THEN** 命令正常结束，每一节都给出可读的空状态说明，而不是抛出未处理的异常

### Requirement: Inspection output does not leak secrets

输出 MUST NOT 包含 `password_hash` 的值、`token_hash` 的值、PDF 字节、嵌入向量的数值，也 MUST NOT 包含数据库口令或任何网关密钥。

#### Scenario: No credentials in the output

- **WHEN** 库里已有用户、会话和片段，操作者运行该命令
- **THEN** 输出里找不到 `password_hash` 的值、`token_hash` 的值、环境变量文件里的数据库口令和嵌入密钥

### Requirement: Inspection is read-only

该命令 MUST 只读取数据库，MUST NOT 增删改任何表里的行，MUST NOT 读取或修改本机 `.env`，也 MUST NOT 停掉或重启正在运行的栈。

#### Scenario: Data unchanged after inspection

- **WHEN** 操作者在栈运行时连续运行该命令两次
- **THEN** 两次输出的用户数、文献数和片段数相同，且 `GET /health` 仍返回 HTTP 200

### Requirement: Missing stack is reported readably

栈没有启动或数据库不可达时，命令 MUST 以非 0 状态退出，并用中文写明需要先启动栈。命令 MUST NOT 抛出未处理的异常堆栈。

#### Scenario: Stack is stopped

- **WHEN** 操作者在没有启动栈的情况下运行该命令
- **THEN** 进程以非 0 状态退出，输出写明需要先启动栈
