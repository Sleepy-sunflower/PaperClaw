## 1. Storage

- [x] 1.1 新增迁移 `002_papers_chunks`，建立 `papers`、`chunks` 和 `ingest_tasks`。片段含 `vector(2048)`。回滚先删 `ingest_tasks`，再删 `chunks`，再删 `papers`。把这三张表的列写入 `docs/data-dictionary.md`。验证：执行向前迁移再回滚这一份，`users` 和 `sessions` 仍在，回滚后 `papers` 和 `ingest_tasks` 不存在；字典里能找到迁移中的每个新列名。

- [x] 1.2 在 `.env.example` 和 `docker-compose.yml` 增加 `EMBEDDING_DIM`，示例文件只有键名。上传进程启动仍允许嵌入配置为空。验证：`.env.example` 中该键的值为空，文件里没有密钥明文；`pytest tests/normal/test_empty_gateway_credentials.py tests/normal/test_health_ok.py` 退出码为 0。

## 2. Ingest API

- [x] 2.1 按 `design.md` 实现上传入队、`GET /api/v1/paper-tasks/{task_id}`、列表、读取单份文献，以及单独的 `python -m app.worker`。接口层不引用 `app.db` 或 `app.adapters`。在 `.cursor/rules/3-security.mdc` 的授权清单写明上传和读取任务必须带令牌。改掉 `openspec/changes/2026-11-04-user-login/specs/user-login/spec.md` 里「文献库不得提供上传控件」的句子和对应 Scenario。验证：`pytest tests/normal/test_paper_ingest.py tests/failure/test_paper_ingest_failures.py tests/boundary/test_paper_upload_size.py` 退出码为 0。用例覆盖上传返回 HTTP 202 且尚未调用嵌入、片段归属、他人不可读、列表隐藏他人文献、缺少令牌、非 PDF、嵌入失败后任务为「失败」且列表为空、20971521 字节被拒绝且不入队、处理进程停着时任务保持「待处理」、同一 PDF 只留一份文献。成功路径的 PDF 由测试用 `pypdf` 在内存中生成。测试替换嵌入发送函数，不访问真实网关。

## 3. Library page

- [x] 3.1 在 `/library` 增加 PDF 上传。用纯文本显示任务状态和「抽字」「切块」「嵌入」「写入」。已可检索后以文本显示文件名，并去掉「还没有文献。」失败时留在文献库。验证：在 `frontend/` 执行 `npm test`，退出码为 0；用例覆盖 Scenario `Library shows the task log`、`Library shows the uploaded filename` 和 `Filename is shown as text`。

## 4. Docs

- [x] 4.1 在 `README.md` 写明登录后于文献库上传 PDF，页面会显示待处理直到已可检索，之后能看到自己的文件名，看不到他人的文献。验证：该节含上传、任务状态和「只列出当前用户」的说明，且没有嵌入密钥的值。
