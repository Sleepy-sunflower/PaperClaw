"""上传与处理的失败路径。"""

from __future__ import annotations

import uuid

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


def _without_request_id(body: dict[str, object]) -> dict[str, object]:
    """去掉每次都会变的请求标识。"""
    copied = dict(body)
    copied.pop("request_id", None)
    return copied


def test_another_user_cannot_read_the_paper(
    client: TestClient,
    monkeypatch,  # type: ignore[no-untyped-def]
    test_database_url: str,
) -> None:
    """Scenario: Another user cannot read the paper"""
    monkeypatch.setattr(
        "app.services.papers.send_embedding",
        lambda base_url, api_key, model, text: [0.5] * 2048,
    )
    text = sample_text()
    token_a = register_and_login(client, "reader-one")
    upload = upload_pdf(client, token_a, make_pdf(text), filename="secret-a.pdf")
    task_id = upload.json()["data"]["task_id"]
    assert process_next_task(test_database_url) is True
    paper_id = client.get(
        "/api/v1/papers", headers={"Authorization": f"Bearer {token_a}"}
    ).json()["data"][0]["id"]

    token_b = register_and_login(client, "reader-two")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    stolen_paper = client.get(f"/api/v1/papers/{paper_id}", headers=headers_b)
    missing_paper = client.get(f"/api/v1/papers/{uuid.uuid4()}", headers=headers_b)
    assert stolen_paper.status_code == 404
    assert stolen_paper.json()["code"] == "not_found"
    assert _without_request_id(stolen_paper.json()) == _without_request_id(
        missing_paper.json()
    )
    assert "secret-a.pdf" not in stolen_paper.text
    assert text[:20] not in stolen_paper.text

    stolen_task = client.get(f"/api/v1/paper-tasks/{task_id}", headers=headers_b)
    missing_task = client.get(f"/api/v1/paper-tasks/{uuid.uuid4()}", headers=headers_b)
    assert stolen_task.status_code == 404
    assert stolen_task.json()["code"] == "not_found"
    assert _without_request_id(stolen_task.json()) == _without_request_id(
        missing_task.json()
    )

    invalid_paper = client.get("/api/v1/papers/not-a-uuid", headers=headers_b)
    assert invalid_paper.status_code == 400
    assert invalid_paper.json()["code"] == "invalid_argument"


def test_list_hides_other_users_papers(
    client: TestClient,
    monkeypatch,  # type: ignore[no-untyped-def]
    test_database_url: str,
) -> None:
    """Scenario: List hides other users' papers"""
    monkeypatch.setattr(
        "app.services.papers.send_embedding",
        lambda base_url, api_key, model, text: [0.5] * 2048,
    )
    text = sample_text()
    token_a = register_and_login(client, "reader-one")
    upload = upload_pdf(client, token_a, make_pdf(text), filename="secret-a.pdf")
    assert upload.status_code == 202
    assert process_next_task(test_database_url) is True

    token_b = register_and_login(client, "reader-two")
    listing = client.get(
        "/api/v1/papers", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert listing.status_code == 200
    assert listing.json()["data"] == []
    assert "secret-a.pdf" not in listing.text
    assert text[:20] not in listing.text


def test_missing_token_is_rejected(client: TestClient) -> None:
    """Scenario: Missing token is rejected"""
    response = client.get("/api/v1/papers")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert "paper.pdf" not in response.text
    assert sample_text()[:20] not in response.text

    upload = client.post(
        "/api/v1/papers",
        files={"file": ("paper.pdf", make_pdf(sample_text()), "application/pdf")},
    )
    assert upload.status_code == 401
    assert upload.json()["code"] == "unauthenticated"

    task = client.get(f"/api/v1/paper-tasks/{uuid.uuid4()}")
    assert task.status_code == 401
    paper = client.get(f"/api/v1/papers/{uuid.uuid4()}")
    assert paper.status_code == 401


def test_reject_a_non_pdf(
    client: TestClient, test_database_url: str
) -> None:
    """Scenario: Reject a non-PDF"""
    token = register_and_login(client, "reader-one")
    response = upload_pdf(client, token, b"this is not a pdf", filename="notes.txt")
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_argument"
    assert client.get(
        "/api/v1/papers", headers={"Authorization": f"Bearer {token}"}
    ).json()["data"] == []
    with psycopg.connect(test_database_url) as connection:
        assert connection.execute("SELECT count(*) FROM ingest_tasks").fetchone()[0] == 0


def test_embedding_failure_stores_nothing(
    client: TestClient,
    monkeypatch,  # type: ignore[no-untyped-def]
    test_database_url: str,
) -> None:
    """Scenario: Embedding failure stores nothing"""
    token = register_and_login(client, "reader-one")
    headers = {"Authorization": f"Bearer {token}"}

    def raise_error(base_url: str, api_key: str, model: str, text: str) -> list[float]:
        raise RuntimeError("embedding gateway down")

    monkeypatch.setattr("app.services.papers.send_embedding", raise_error)
    upload = upload_pdf(client, token, make_pdf(sample_text()), filename="broken.pdf")
    assert upload.status_code == 202
    assert process_next_task(test_database_url) is True
    task = client.get(
        f"/api/v1/paper-tasks/{upload.json()['data']['task_id']}", headers=headers
    ).json()["data"]
    assert task["status"] == "失败"
    assert client.get("/api/v1/papers", headers=headers).json()["data"] == []

    def short_vector(base_url: str, api_key: str, model: str, text: str) -> list[float]:
        return [0.5] * 10

    monkeypatch.setattr("app.services.papers.send_embedding", short_vector)
    upload = upload_pdf(client, token, make_pdf(sample_text(150)), filename="short.pdf")
    assert upload.status_code == 202
    assert process_next_task(test_database_url) is True
    task = client.get(
        f"/api/v1/paper-tasks/{upload.json()['data']['task_id']}", headers=headers
    ).json()["data"]
    assert task["status"] == "失败"
    assert client.get("/api/v1/papers", headers=headers).json()["data"] == []

    with psycopg.connect(test_database_url) as connection:
        assert connection.execute("SELECT count(*) FROM papers").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0
    assert "test-embedding-key" not in client.get("/api/v1/papers", headers=headers).text
