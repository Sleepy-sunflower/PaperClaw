# 文献引路

面向个人研究的文献阅读助手。用户上传自己的论文并向阅读助手提问，助手只依据该用户的文献库和本次检索到的出处回答。


## 本机运行

需要已安装 Git 与 Docker Desktop（含 Docker Compose）。

```powershell
git clone <仓库地址>
cd paperclaw
Copy-Item .env.example .env
docker compose up --build
```

macOS 或 Linux 把复制环境文件的那一行换成 `cp .env.example .env`。

填写 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB`。`DATABASE_URL` 使用同一套账号，主机名为 `db`，端口为 `5432`。`LLM_*` 和 `EMBEDDING_*` 可以留空。

启动后访问 [http://localhost:8000/health](http://localhost:8000/health)。返回应用与数据库的连通状态即表示启动成功。

密钥只写在本机的 `.env` 里。`.env.example` 只保留键名。

## 测试

Python 测试不需要额外的环境变量，也不会连接 Compose 里正在使用的数据库。在仓库根目录执行：

```powershell
pytest --junitxml=test-reports/junit.xml
```

退出码 `0` 表示通过。报告写在 `test-reports/junit.xml`。

已按上面的步骤启动后，可用 `PAPERCLAW_LIVE=1` 再跑一次，以检查本机的 `GET /health`。不设置时，对应用例会跳过。

前端组件测试在 `frontend/` 目录执行 `npm test`。退出码 `0` 表示通过。

