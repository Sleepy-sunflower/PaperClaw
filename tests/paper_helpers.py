"""在内存中生成 PDF、准备测试库并登录测试用户。"""

from __future__ import annotations

import io

import psycopg
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def make_pdf(text: str) -> bytes:
    """写一页正文为给定文本的 PDF。文本只用 ASCII 字符。"""
    writer = PdfWriter()
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
    stream.set_data(f"BT /F1 12 Tf 72 700 Td ({escaped}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def sample_text(word_count: int = 120) -> str:
    """生成一段长于 400 个字符的正文。"""
    return " ".join(f"w{index}" for index in range(word_count))


def reset_database(database_url: str) -> None:
    """清空用户，级联清空会话、文献、片段和任务。"""
    with psycopg.connect(database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()


def register_and_login(
    client: TestClient,
    username: str,
    password: str = "password1",
) -> str:
    """注册并登录一个用户，返回令牌。"""
    client.post("/api/v1/users", json={"username": username, "password": password})
    response = client.post(
        "/api/v1/sessions",
        json={"username": username, "password": password},
    )
    return str(response.json()["data"]["token"])


def upload_pdf(
    client: TestClient,
    token: str,
    content: bytes,
    filename: str = "paper.pdf",
):  # type: ignore[no-untyped-def]
    """以表单字段 file 上传一份文件。"""
    return client.post(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, "application/pdf")},
    )
