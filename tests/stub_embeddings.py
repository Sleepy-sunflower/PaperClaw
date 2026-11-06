"""本地桩嵌入端点：返回确定性的 2048 维向量，供端到端验证使用。

用法：python tests/stub_embeddings.py [端口]，默认监听 8100。
每次请求向日志 tmp/stub_embeddings.log 追加一行 JSON，
记录路径、Authorization 是否匹配桩密钥、请求体的键和 input 长度。
密钥是写死的假值，只用于本机验证，不是任何真实网关的凭证。
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "tmp" / "stub_embeddings.log"
STUB_API_KEY = "e2e-stub-key"
DIM = 2048


class Handler(BaseHTTPRequestHandler):
    """处理 POST /embeddings，其余请求一律拒绝。"""

    def do_POST(self) -> None:  # noqa: N802
        """校验桩密钥，记录请求摘要，返回确定性向量。"""
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        auth = self.headers.get("Authorization", "")
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as log:
            log.write(
                json.dumps(
                    {
                        "path": self.path,
                        "auth_ok": auth == f"Bearer {STUB_API_KEY}",
                        "body_keys": sorted(body.keys()),
                        "model": body.get("model"),
                        "input_len": len(body.get("input", "")),
                    }
                )
                + "\n"
            )
        if self.path != "/embeddings" or auth != f"Bearer {STUB_API_KEY}":
            self.send_response(401)
            self.end_headers()
            return
        digest = hashlib.sha256(str(body.get("input", "")).encode()).digest()
        seed = struct.unpack(">Q", digest[:8])[0]
        values = [((seed * (index + 1) * 2654435761) % 1000) / 500.0 - 1.0 for index in range(DIM)]
        payload = json.dumps(
            {"data": [{"embedding": values, "index": 0}], "model": body.get("model")}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        """不向标准错误输出访问日志。"""


def main() -> None:
    """监听端口，直到进程被停掉。"""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8100
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
