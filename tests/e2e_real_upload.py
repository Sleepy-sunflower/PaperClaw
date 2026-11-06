"""端到端真实上传验证：用真栈、真 HTTP、真处理进程，嵌入端点用本地桩。

用法（仓库根目录）：

    python tests/e2e_real_upload.py

它会：
1. 在 tmp/ 生成一份两页、每页正文长于 400 字符的真实 PDF（可以打开看）；
2. 启动 tests/stub_embeddings.py 作为本地嵌入端点（返回 2048 维向量）；
3. 拆掉上一次可能残留的栈和数据卷，再用 tests/e2e-compose.env 拉起独立的 Compose 栈
   （项目名 paperclaw-e2e），把 EMBEDDING_* 指向本机桩，并用 tests/e2e-ports.yml 把宿主机
   端口挪到 18000，避免和操作者日常运行的栈冲突；
4. 走真实 HTTP：注册、登录、上传 PDF，轮询任务到「已可检索」，确认文献库列出文件名；
5. 用第二个用户确认看不到别人的文献，读取别人的文献返回 404；
6. 拆栈并停掉桩。

不改本机 .env，不访问任何真实网关。生成的 PDF 和桩日志都留在 tmp/ 里可查看。
"""

from __future__ import annotations

import io
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
STUB = ROOT / "tests" / "stub_embeddings.py"
ENV_FILE = ROOT / "tests" / "e2e-compose.env"
PORTS_FILE = ROOT / "tests" / "e2e-ports.yml"
PROJECT = "paperclaw-e2e"
BASE = "http://localhost:18000"
STUB_PORT = 8100
PDF_PATH = TMP / "sample-paper.pdf"

_checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    """记录一条检查结论，并在最后据此决定退出码。"""
    _checks.append((name, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {name}{(' — ' + detail) if detail else ''}", flush=True)


def make_pdf(pages: list[str]) -> bytes:
    """把每一页的正文写进一份 PDF。正文只用 ASCII 字符。"""
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=720, height=720)
        font = DictionaryObject()
        font.update(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)
        resources = DictionaryObject()
        resources[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font_ref})
        page[NameObject("/Resources")] = resources
        stream = DecodedStreamObject()
        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream.set_data(f"BT /F1 12 Tf 40 700 Td 16 TL ({escaped}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def compose(*args: str) -> subprocess.CompletedProcess[str]:
    """在独立项目名下执行 docker compose，宿主机端口用 tests/e2e-ports.yml 挪开。"""
    return subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            PROJECT,
            "--env-file",
            str(ENV_FILE),
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            str(PORTS_FILE),
            *args,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def wait_http_ok(url: str, attempts: int = 30, delay: float = 1.0) -> bool:
    """轮询一个 HTTP 地址，直到返回 200。"""
    for _ in range(attempts):
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def wait_tcp_open(port: int, attempts: int = 30, delay: float = 1.0) -> bool:
    """轮询本机 TCP 端口，直到能建立连接。"""
    for _ in range(attempts):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except OSError:
            time.sleep(delay)
    return False


def main() -> int:
    """执行端到端流程，返回退出码。"""
    TMP.mkdir(exist_ok=True)
    (TMP / "stub_embeddings.log").unlink(missing_ok=True)

    pages = [
        " ".join(f"alpha{i}" for i in range(90)),
        " ".join(f"beta{i}" for i in range(90)),
    ]
    PDF_PATH.write_bytes(make_pdf(pages))
    print(f"生成 PDF：{PDF_PATH}（{PDF_PATH.stat().st_size} 字节，{len(pages)} 页）", flush=True)

    stub = subprocess.Popen([sys.executable, str(STUB), str(STUB_PORT)])
    try:
        if not wait_tcp_open(STUB_PORT, attempts=10):
            print("桩嵌入端点没有就绪", flush=True)
            return 1

        compose("down", "-v")
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
        check("health 数据库连通", health.get("checks", {}).get("database") == "up")

        run_flow()
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


def run_flow() -> None:
    """注册、登录、上传、轮询、列表和隐私检查。"""
    password = "password1"
    with httpx.Client(base_url=BASE, timeout=10) as client:
        client.post("/api/v1/users", json={"username": "e2e-reader-one", "password": password})
        login = client.post(
            "/api/v1/sessions",
            json={"username": "e2e-reader-one", "password": password},
        )
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        with PDF_PATH.open("rb") as handle:
            upload = client.post(
                "/api/v1/papers",
                headers=headers,
                files={"file": ("sample-paper.pdf", handle, "application/pdf")},
            )
        check("上传返回 202", upload.status_code == 202, str(upload.status_code))
        data = upload.json()["data"]
        task_id = data["task_id"]
        check("上传后状态为待处理", data["status"] == "待处理", data["status"])

        status = ""
        log: list[str] = []
        for _ in range(150):
            task = client.get(f"/api/v1/paper-tasks/{task_id}", headers=headers).json()["data"]
            status, log = task["status"], task["log"]
            if status in ("已可检索", "失败"):
                break
            time.sleep(2)
        check("任务最终为已可检索", status == "已可检索", f"{status} log={log}")
        check(
            "任务日志记录四个步骤",
            log == ["抽字", "切块", "嵌入", "写入"],
            str(log),
        )

        papers = client.get("/api/v1/papers", headers=headers).json()["data"]
        names = [paper["filename"] for paper in papers]
        check("文献库列出上传的文件名", names == ["sample-paper.pdf"], str(names))
        check("响应里没有桩密钥", "e2e-stub-key" not in client.get("/api/v1/papers", headers=headers).text)

        client.post("/api/v1/users", json={"username": "e2e-reader-two", "password": password})
        token_b = client.post(
            "/api/v1/sessions",
            json={"username": "e2e-reader-two", "password": password},
        ).json()["data"]["token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        other_papers = client.get("/api/v1/papers", headers=headers_b).json()["data"]
        check("第二个用户列表为空", other_papers == [], str(other_papers))
        if papers:
            stolen = client.get(f"/api/v1/papers/{papers[0]['id']}", headers=headers_b)
            check("第二个用户读别人的文献得到 404", stolen.status_code == 404, str(stolen.status_code))
        stolen_task = client.get(f"/api/v1/paper-tasks/{task_id}", headers=headers_b)
        check("第二个用户读别人的任务得到 404", stolen_task.status_code == 404, str(stolen_task.status_code))


if __name__ == "__main__":
    raise SystemExit(main())
