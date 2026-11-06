"""上传大小的边界。"""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app
from tests.paper_helpers import register_and_login, reset_database, upload_pdf

_LIMIT = 20971520


@pytest.fixture
def client(monkeypatch, test_database_url: str):  # type: ignore[no-untyped-def]
    """每个用例使用已迁移的独立测试库。"""
    migrate_up(test_database_url)
    reset_database(test_database_url)
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    yield TestClient(create_app())
    reset_database(test_database_url)


def test_one_byte_over_limit_is_rejected_and_not_queued(
    client: TestClient, test_database_url: str
) -> None:
    """Scenario: Upload returns before embedding（大小上限之外一个字节被拒绝）"""
    token = register_and_login(client, "reader-one")
    content = b"%PDF-1.4\n" + b"%" * (_LIMIT + 1 - 9)
    assert len(content) == _LIMIT + 1
    response = upload_pdf(client, token, content)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_argument"
    with psycopg.connect(test_database_url) as connection:
        assert connection.execute("SELECT count(*) FROM ingest_tasks").fetchone()[0] == 0


def test_exact_limit_is_accepted(client: TestClient) -> None:
    """Scenario: Upload returns before embedding（大小上限本身被接受）"""
    token = register_and_login(client, "reader-one")
    content = b"%PDF-1.4\n" + b"%" * (_LIMIT - 9)
    assert len(content) == _LIMIT
    response = upload_pdf(client, token, content)
    assert response.status_code == 202
    assert response.json()["code"] == "ok"
    assert response.json()["data"]["status"] == "待处理"
