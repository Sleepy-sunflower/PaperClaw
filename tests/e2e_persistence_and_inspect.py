"""端到端验证：数据持久化 + 数据库可视化脚本。

用法（仓库根目录）：

    python tests/e2e_persistence_and_inspect.py

它会：
1. 在 tmp/ 生成一份两页的真实 PDF（可以打开看）；
2. 启动 tests/stub_embeddings.py 作为本地嵌入端点；
3. 用 tests/e2e-compose.env 拉起独立的 Compose 栈（项目名 paperclaw-e2e，宿主机端口按
   tests/e2e-ports.yml 挪到 18000，不和日常运行的栈冲突）；
4. 注册用户、上传 PDF、轮询到「已可检索」；
5. `docker compose down`（不带 -v）后重新 `up -d`，确认同一组用户名密码仍能登录、
   文献仍在列表里；
6. 运行 tools/db_inspect.py 指向这个栈，确认输出里有用户名、文件名和 PDF 正文里的词，
   并且不含口令哈希、令牌摘要和桩密钥；连跑两次确认脚本只读；
7. 拆栈（down -v）并停掉桩。

不改本机 .env，不访问任何真实网关。生成的 PDF、桩日志和可视化报告都留在 tmp/ 里。
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

import httpx

from e2e_real_upload import (
    BASE,
    ENV_FILE,
    PROJECT,
    STUB,
    STUB_PORT,
    compose,
    make_pdf,
    wait_http_ok,
    wait_tcp_open,
)

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
PDF_PATH = TMP / "persistence-paper.pdf"
INSPECTOR = ROOT / "tools" / "db_inspect.py"
REPORT_PATH = TMP / "db-inspect-e2e.txt"

USERNAME = "e2e-persist-reader"
PASSWORD = "password1"
FILENAME = "persistence-paper.pdf"
MARKER = "persistmarker"

_checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    """记录一条检查结论，并在最后据此决定退出码。"""
    _checks.append((name, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {name}{(' — ' + detail) if detail else ''}", flush=True)


def inspect_database() -> subprocess.CompletedProcess[str]:
    """对独立栈运行可视化脚本，返回它的执行结果。"""
    return subprocess.run(
        [
            sys.executable,
            str(INSPECTOR),
            "--project",
            PROJECT,
            "--env-file",
            str(ENV_FILE),
            "--output",
            str(REPORT_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def main() -> int:
    """执行端到端流程，返回退出码。"""
    TMP.mkdir(exist_ok=True)
    (TMP / "stub_embeddings.log").unlink(missing_ok=True)
    REPORT_PATH.unlink(missing_ok=True)

    pages = [
        MARKER + " " + " ".join(f"gamma{i}" for i in range(90)),
        " ".join(f"delta{i}" for i in range(90)),
    ]
    PDF_PATH.write_bytes(make_pdf(pages))
    print(f"生成 PDF：{PDF_PATH}（{PDF_PATH.stat().st_size} 字节，{len(pages)} 页）", flush=True)

    compose("down", "-v")
    stub = subprocess.Popen([sys.executable, str(STUB), str(STUB_PORT)])
    try:
        if not wait_tcp_open(STUB_PORT, attempts=10):
            print("桩嵌入端点没有就绪", flush=True)
            return 1

        up = compose("up", "--build", "-d")
        if up.returncode != 0:
            print(up.stdout, up.stderr, flush=True)
            check("compose up", False, "启动失败")
            return 1
        if not wait_http_ok(f"{BASE}/health", attempts=60, delay=2):
            print(compose("logs", "api", "worker").stdout, flush=True)
            check("health", False, "60 次轮询后仍不可达")
            return 1
        health = httpx.get(f"{BASE}/health", timeout=5).json()
        check("启动后数据库连通", health.get("checks", {}).get("database") == "up")

        token = register_and_upload()
        restart_stack()
        token = login_after_restart(token)
        check_inspection(token)
    finally:
        compose("down", "-v")
        stub.terminate()
        try:
            stub.wait(timeout=5)
        except subprocess.TimeoutExpired:
            stub.kill()

    failed = [name for name, ok, _ in _checks if not ok]
    print(
        f"\n共 {len(_checks)} 项检查，失败 {len(failed)} 项"
        + (f"：{', '.join(failed)}" if failed else ""),
        flush=True,
    )
    return 1 if failed else 0


def register_and_upload() -> str:
    """注册用户、上传 PDF 并等到任务成为「已可检索」，返回登录令牌。"""
    with httpx.Client(base_url=BASE, timeout=10) as client:
        registered = client.post(
            "/api/v1/users", json={"username": USERNAME, "password": PASSWORD}
        )
        check("注册返回 201", registered.status_code == 201, str(registered.status_code))
        token = client.post(
            "/api/v1/sessions", json={"username": USERNAME, "password": PASSWORD}
        ).json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        with PDF_PATH.open("rb") as handle:
            upload = client.post(
                "/api/v1/papers",
                headers=headers,
                files={"file": (FILENAME, handle, "application/pdf")},
            )
        check("上传返回 202", upload.status_code == 202, str(upload.status_code))
        task_id = upload.json()["data"]["task_id"]

        status = ""
        started = time.monotonic()
        for _ in range(150):
            task = client.get(f"/api/v1/paper-tasks/{task_id}", headers=headers).json()["data"]
            status = task["status"]
            if status in ("已可检索", "失败"):
                break
            time.sleep(2)
        waited = int(time.monotonic() - started)
        check("任务最终为已可检索", status == "已可检索", f"{status}，等了 {waited} 秒")
        if status != "已可检索":
            print(compose("logs", "--tail", "40", "worker").stdout, flush=True)

        names = [p["filename"] for p in client.get("/api/v1/papers", headers=headers).json()["data"]]
        check("重启前列表含上传的文件名", names == [FILENAME], str(names))
    return token


def restart_stack() -> None:
    """不带 -v 拆栈，再重新起栈，确认数据库仍然连通。"""
    down = compose("down")
    check("down 不带 -v 成功", down.returncode == 0, down.stderr.strip()[-200:])
    up = compose("up", "-d")
    check("重新 up 成功", up.returncode == 0, up.stderr.strip()[-200:])
    check("重启后 health 可达", wait_http_ok(f"{BASE}/health", attempts=60, delay=2))
    health = httpx.get(f"{BASE}/health", timeout=5).json()
    check("重启后数据库连通", health.get("checks", {}).get("database") == "up")


def login_after_restart(old_token: str) -> str:
    """用同一组用户名和密码登录，确认用户和文献都还在。"""
    with httpx.Client(base_url=BASE, timeout=10) as client:
        login = client.post("/api/v1/sessions", json={"username": USERNAME, "password": PASSWORD})
        check("重启后同一组凭证登录返回 200", login.status_code == 200, str(login.status_code))
        if login.status_code != 200:
            return old_token
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        names = [p["filename"] for p in client.get("/api/v1/papers", headers=headers).json()["data"]]
        check("重启后列表仍含该文件名", names == [FILENAME], str(names))
        return token


def check_inspection(token: str) -> None:
    """运行可视化脚本两次，检查内容、只读性和不泄露凭证。"""
    first = inspect_database()
    check("可视化脚本退出码为 0", first.returncode == 0, first.stderr.strip()[-200:])
    report = first.stdout
    print(report, flush=True)

    check("输出含用户名", USERNAME in report)
    check("输出含文件名", FILENAME in report)
    check("输出含任务状态", "已可检索" in report)
    check("输出含 PDF 正文里的词", MARKER in report)
    check("输出含片段页码", "第 1 页" in report and "第 2 页" in report)

    check("输出不含口令哈希", "$argon2" not in report)
    check("输出不含令牌", token not in report)
    check("输出不含令牌摘要", hashlib.sha256(token.encode()).hexdigest() not in report)
    check("输出不含桩密钥", "e2e-stub-key" not in report)
    check("报告文件已写出", REPORT_PATH.exists() and MARKER in REPORT_PATH.read_text(encoding="utf-8"))

    second = inspect_database()
    check("连续两次输出一致（脚本只读）", second.stdout == report)
    check("查看之后 health 仍可达", httpx.get(f"{BASE}/health", timeout=5).status_code == 200)


if __name__ == "__main__":
    raise SystemExit(main())
