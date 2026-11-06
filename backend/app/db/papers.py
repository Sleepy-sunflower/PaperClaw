"""文献、片段和入库任务的数据库访问。"""

from __future__ import annotations

from typing import TypedDict

import psycopg


class TaskRow(TypedDict):
    """ingest_tasks 表中处理一条任务需要的列。"""

    id: str
    user_id: str
    filename: str
    content_sha256: str
    pdf: bytes


class TaskView(TypedDict):
    """任务状态接口返回的列。"""

    status: str
    log: list[str]


class PaperView(TypedDict):
    """文献接口返回的列。"""

    id: str
    filename: str


def insert_task(
    database_url: str,
    user_id: str,
    filename: str,
    content_sha256: str,
    pdf: bytes,
) -> str:
    """插入一条「待处理」任务并返回任务标识。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            INSERT INTO ingest_tasks (user_id, filename, content_sha256, pdf, status)
            VALUES (%s, %s, %s, %s, '待处理')
            RETURNING id
            """,
            (user_id, filename, content_sha256, psycopg.Binary(pdf)),
        ).fetchone()
        connection.commit()
    return str(row[0])


def find_task_by_content(
    database_url: str,
    user_id: str,
    content_sha256: str,
) -> dict[str, str] | None:
    """按用户和内容哈希取出已有任务。没有时返回 None。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT id, status
            FROM ingest_tasks
            WHERE user_id = %s AND content_sha256 = %s
            """,
            (user_id, content_sha256),
        ).fetchone()
    if row is None:
        return None
    return {"id": str(row[0]), "status": str(row[1])}


def claim_next_task(database_url: str) -> TaskRow | None:
    """领取一条任务并改为「处理中」，同时清空日志。没有可领取时返回 None。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            UPDATE ingest_tasks
            SET status = '处理中', log = '{}'
            WHERE id = (
                SELECT id
                FROM ingest_tasks
                WHERE status IN ('待处理', '处理中')
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, user_id, filename, content_sha256, pdf
            """
        ).fetchone()
        connection.commit()
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "user_id": str(row[1]),
        "filename": str(row[2]),
        "content_sha256": str(row[3]),
        "pdf": bytes(row[4]),
    }


def append_task_log(database_url: str, task_id: str, entry: str) -> None:
    """把一步处理记录追加到任务日志。"""
    with psycopg.connect(database_url) as connection:
        connection.execute(
            "UPDATE ingest_tasks SET log = array_append(log, %s) WHERE id = %s",
            (entry, task_id),
        )
        connection.commit()


def mark_task_failed(database_url: str, task_id: str) -> None:
    """把任务标为「失败」。"""
    with psycopg.connect(database_url) as connection:
        connection.execute(
            "UPDATE ingest_tasks SET status = '失败' WHERE id = %s",
            (task_id,),
        )
        connection.commit()


def store_paper(
    database_url: str,
    task_id: str,
    user_id: str,
    filename: str,
    content_sha256: str,
    chunks: list[tuple[int, str, list[float]]],
) -> str:
    """在一个事务里写入文献和片段，并把任务改为「已可检索」。

    同一用户同一内容已有文献时不再插第二份，只把任务指向已有文献。
    返回文献标识。
    """
    with psycopg.connect(database_url) as connection:
        existing = connection.execute(
            "SELECT id FROM papers WHERE user_id = %s AND content_sha256 = %s",
            (user_id, content_sha256),
        ).fetchone()
        if existing is not None:
            paper_id = str(existing[0])
        else:
            row = connection.execute(
                """
                INSERT INTO papers (user_id, filename, content_sha256)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (user_id, filename, content_sha256),
            ).fetchone()
            paper_id = str(row[0])
            for page, content, embedding in chunks:
                connection.execute(
                    """
                    INSERT INTO chunks (paper_id, user_id, page, content, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    """,
                    (paper_id, user_id, page, content, _vector_literal(embedding)),
                )
        connection.execute(
            """
            UPDATE ingest_tasks
            SET status = '已可检索', paper_id = %s, log = array_append(log, '写入')
            WHERE id = %s
            """,
            (paper_id, task_id),
        )
        connection.commit()
    return paper_id


def _vector_literal(embedding: list[float]) -> str:
    """把向量写成 pgvector 的字面量。"""
    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"


def find_task_for_user(
    database_url: str,
    task_id: str,
    user_id: str,
) -> TaskView | None:
    """按标识取出属于该用户的任务状态和日志。没有时返回 None。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT status, log
            FROM ingest_tasks
            WHERE id = %s AND user_id = %s
            """,
            (task_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return {"status": str(row[0]), "log": [str(entry) for entry in row[1]]}


def list_papers(database_url: str, user_id: str) -> list[PaperView]:
    """列出该用户已入库的文献标识和文件名。"""
    with psycopg.connect(database_url) as connection:
        rows = connection.execute(
            """
            SELECT id, filename
            FROM papers
            WHERE user_id = %s
            ORDER BY created_at
            """,
            (user_id,),
        ).fetchall()
    return [{"id": str(row[0]), "filename": str(row[1])} for row in rows]


def find_paper_for_user(
    database_url: str,
    paper_id: str,
    user_id: str,
) -> PaperView | None:
    """按标识取出属于该用户的文献。没有时返回 None。"""
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT id, filename
            FROM papers
            WHERE id = %s AND user_id = %s
            """,
            (paper_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return {"id": str(row[0]), "filename": str(row[1])}
