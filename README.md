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

启动后访问 [http://localhost:8000/health](http://localhost:8000/health)。返回应用与数据库的连通状态即表示启动成功。

密钥只写在本机的 `.env` 里。`.env.example` 只保留键名。
