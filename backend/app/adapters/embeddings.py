"""嵌入接口的出站请求。"""

from __future__ import annotations

import httpx


def send_embedding(base_url: str, api_key: str, model: str, text: str) -> list[float]:
    """把一块正文提交给嵌入接口，返回向量。

    请求体只有 model 和 input，不提交维度。失败时抛出异常。
    """
    url = base_url.rstrip("/") + "/embeddings"
    response = httpx.post(
        url,
        json={"model": model, "input": text},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return [float(value) for value in payload["data"][0]["embedding"]]
