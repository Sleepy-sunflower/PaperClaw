"""上传入队、处理进程和文献归属的正常路径。"""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app
from app.services.papers import process_next_task
from tests.paper_helpers import (
    make_pdf,
    register_and_login,
    reset_database,
    sample_text,
    upload_pdf,
)


@pytest.fixture
def client(monkeypatch, test_database_url: str):  # type: ignore[no-untyped-def]
    """每个用例使用已迁移的独立测试库，嵌入配置齐全但不访问真实网关。"""
    migrate_up(test_database_url)
    reset_database(test_database_url)
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://embed.example")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "test-model")
    monkeypatch.setenv("EMBEDDING_DIM", "2048")
    yield TestClient(create_app())
    reset_database(test_database_url)


@pytest.fixture
def embedding_calls(monkeypatch):  # type: ignore[no-untyped-def]
    """替换适配层的嵌入发送函数，并记录每次提交的正文。"""
    calls: list[str] = []

    def fake_send(base_url: str, api_key: str, model: str, text: str) -> list[float]:
        calls.append(text)
        return [0.5] * 2048

    monkeypatch.setattr("app.services.papers.send_embedding", fake_send)
    return calls


def test_upload_returns_before_embedding(
    client: TestClient, embedding_calls: list[str]
) -> None:
    """Scenario: Upload returns before embedding"""
    token = register_and_login(client, "reader-one")
    response = upload_pdf(client, token, make_pdf(sample_text()))
    assert response.status_code == 202
    body = response.json()
    assert body["code"] == "ok"
    assert body["data"]["status"] == "待处理"
    assert isinstance(body["data"]["task_id"], str) and body["data"]["task_id"]
    assert embedding_calls == []
    assert sample_text()[:20] not in response.text


def test_stored_chunks_belong_to_uploader(
    client: TestClient,
    embedding_calls: list[str],
    test_database_url: str,
) -> None:
    """Scenario: Stored chunks belong to the uploader"""
    token = register_and_login(client, "reader-one")
    text = sample_text()
    upload = upload_pdf(client, token, make_pdf(text))
    task_id = upload.json()["data"]["task_id"]
    assert process_next_task(test_database_url) is True

    task = client.get(
        f"/api/v1/paper-tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["data"]
    assert task["status"] == "已可检索"
    assert task["log"] == ["抽字", "切块", "嵌入", "写入"]

    papers = client.get(
        "/api/v1/papers",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["data"]
    assert [paper["filename"] for paper in papers] == ["paper.pdf"]

    with psycopg.connect(test_database_url) as connection:
        rows = connection.execute(
            """
            SELECT chunks.user_id = papers.user_id, page, content, vector_dims(embedding)
            FROM chunks
            JOIN papers ON papers.id = chunks.paper_id
            WHERE papers.user_id = (SELECT id FROM users WHERE username = 'reader-one')
            ORDER BY chunks.ctid
            """
        ).fetchall()
    assert rows, "至少要有一个片段"
    assert all(row[0] for row in rows), "片段必须属于上传者"
    assert all(row[1] >= 1 for row in rows), "片段记有页码"
    assert all(len(row[2]) <= 400 for row in rows), "片段正文不超过 400 个字符"
    assert all(row[3] == 2048 for row in rows), "每个向量长度为 2048"
    assert len(rows) >= 2, "长于一页 400 字符的正文要切出多个片段"
    for previous, following in zip(rows, rows[1:]):
        if previous[1] == following[1]:
            assert previous[2][-80:] == following[2][:80], "同一页相邻片段重叠 80 个字符"
    assert embedding_calls, "嵌入按块提交"


def test_stopped_worker_keeps_the_task(
    client: TestClient,
    embedding_calls: list[str],
    test_database_url: str,
) -> None:
    """Scenario: Stopped worker keeps the task"""
    token = register_and_login(client, "reader-one")
    upload = upload_pdf(client, token, make_pdf(sample_text()))
    assert upload.status_code == 202
    task_id = upload.json()["data"]["task_id"]

    headers = {"Authorization": f"Bearer {token}"}
    task = client.get(f"/api/v1/paper-tasks/{task_id}", headers=headers).json()["data"]
    assert task["status"] == "待处理"
    assert client.get("/api/v1/papers", headers=headers).json()["data"] == []

    assert process_next_task(test_database_url) is True
    task = client.get(f"/api/v1/paper-tasks/{task_id}", headers=headers).json()["data"]
    assert task["status"] == "已可检索"
    assert len(client.get("/api/v1/papers", headers=headers).json()["data"]) == 1


def test_duplicate_upload_stores_one_paper(
    client: TestClient,
    embedding_calls: list[str],
    test_database_url: str,
) -> None:
    """Scenario: Duplicate upload stores one paper"""
    token = register_and_login(client, "reader-one")
    content = make_pdf(sample_text())
    first = upload_pdf(client, token, content)
    second = upload_pdf(client, token, content)
    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["data"]["task_id"] == first.json()["data"]["task_id"]

    assert process_next_task(test_database_url) is True
    assert process_next_task(test_database_url) is False

    with psycopg.connect(test_database_url) as connection:
        papers = connection.execute("SELECT count(*) FROM papers").fetchone()[0]
        chunks = connection.execute("SELECT count(*) FROM chunks").fetchone()[0]
        tasks = connection.execute("SELECT count(*) FROM ingest_tasks").fetchone()[0]
    assert papers == 1
    assert tasks == 1
    assert chunks > 0

    headers = {"Authorization": f"Bearer {token}"}
    assert len(client.get("/api/v1/papers", headers=headers).json()["data"]) == 1
