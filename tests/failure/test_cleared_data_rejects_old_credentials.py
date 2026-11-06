"""清空数据之后，原先的凭证不再能用。"""

from __future__ import annotations

import psycopg
from fastapi.testclient import TestClient

from app.db.migrate import migrate_up
from app.main import create_app

_USERNAME = "reader-one"
_PASSWORD = "password1"


def test_cleared_data_rejects_old_credentials(
    monkeypatch, test_database_url: str  # type: ignore[no-untyped-def]
) -> None:
    """Scenario: down -v clears the data

    清空测试库等价于换成一个空卷：卷里只有数据库数据，`docker compose down -v`
    删掉卷之后重新启动的栈看到的就是一个空库。
    """
    migrate_up(test_database_url)
    with psycopg.connect(test_database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    client = TestClient(create_app())

    registered = client.post(
        "/api/v1/users", json={"username": _USERNAME, "password": _PASSWORD}
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/v1/sessions", json={"username": _USERNAME, "password": _PASSWORD}
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["data"]["token"]
    assert (
        client.get(
            "/api/v1/sessions/current", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 200
    )

    with psycopg.connect(test_database_url) as connection:
        connection.execute("TRUNCATE sessions, users CASCADE")
        connection.commit()

    after_clear = client.post(
        "/api/v1/sessions", json={"username": _USERNAME, "password": _PASSWORD}
    )
    assert after_clear.status_code == 401
    assert after_clear.json()["code"] == "unauthenticated"
    assert _USERNAME not in after_clear.text

    old_token = client.get(
        "/api/v1/sessions/current", headers={"Authorization": f"Bearer {token}"}
    )
    assert old_token.status_code == 401
    assert old_token.json()["code"] == "unauthenticated"
