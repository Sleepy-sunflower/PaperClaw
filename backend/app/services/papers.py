"""上传入队、任务与文献读取，以及处理进程的业务。"""

from __future__ import annotations

import hashlib
import io
import os
import uuid
from typing import Literal

from pypdf import PdfReader

from app.adapters.embeddings import send_embedding
from app.db.papers import (
    append_task_log,
    claim_next_task,
    find_paper_for_user,
    find_task_by_content,
    find_task_for_user,
    insert_task,
    list_papers,
    mark_task_failed,
    store_paper,
)

MAX_UPLOAD_BYTES = 20971520
_REQUIRED_DIM = 2048
_WINDOW = 400
_STEP = 320

UploadOutcome = tuple[Literal["invalid"]] | tuple[Literal["accepted"], str, str]
ReadOutcome = tuple[Literal["invalid"] | Literal["missing"]] | tuple[Literal["found"], dict[str, object]]


def accept_upload(
    database_url: str,
    user_id: str,
    filename: str,
    content: bytes,
) -> UploadOutcome:
    """校验上传并放入任务。成功时返回任务标识和当前状态。

    同一用户同一内容已有任务时不再入队，返回已有任务。
    """
    if len(content) > MAX_UPLOAD_BYTES:
        return ("invalid",)
    if not content.startswith(b"%PDF"):
        return ("invalid",)
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if not 1 <= len(name) <= 200:
        return ("invalid",)
    content_sha256 = hashlib.sha256(content).hexdigest()
    existing = find_task_by_content(database_url, user_id, content_sha256)
    if existing is not None:
        return ("accepted", existing["id"], existing["status"])
    task_id = insert_task(database_url, user_id, name, content_sha256, content)
    return ("accepted", task_id, "待处理")


def read_task(database_url: str, user_id: str, task_id: str) -> ReadOutcome:
    """读取属于该用户的任务状态和日志。他人的任务与不存在的任务同样返回 missing。"""
    if not _is_uuid(task_id):
        return ("invalid",)
    task = find_task_for_user(database_url, task_id, user_id)
    if task is None:
        return ("missing",)
    return ("found", {"task_id": task_id, "status": task["status"], "log": task["log"]})


def list_ready_papers(database_url: str, user_id: str) -> list[dict[str, str]]:
    """列出该用户已可检索的文献标识和文件名。"""
    return list_papers(database_url, user_id)


def read_paper(database_url: str, user_id: str, paper_id: str) -> ReadOutcome:
    """读取属于该用户的一份文献。他人的文献与不存在的文献同样返回 missing。"""
    if not _is_uuid(paper_id):
        return ("invalid",)
    paper = find_paper_for_user(database_url, paper_id, user_id)
    if paper is None:
        return ("missing",)
    return ("found", {"id": paper["id"], "filename": paper["filename"]})


def process_next_task(database_url: str) -> bool:
    """领取并做完一条任务。没有可领取的任务时返回 False。"""
    task = claim_next_task(database_url)
    if task is None:
        return False
    _process(database_url, task)
    return True


def _process(database_url: str, task: dict[str, object]) -> None:
    """按「抽字」「切块」「嵌入」「写入」做完一条任务。任一步失败则标为「失败」。"""
    task_id = str(task["id"])
    try:
        pages = _extract_pages(bytes(task["pdf"]))  # type: ignore[arg-type]
    except Exception:
        mark_task_failed(database_url, task_id)
        return
    if not pages:
        mark_task_failed(database_url, task_id)
        return
    append_task_log(database_url, task_id, "抽字")
    pieces = _chunk_pages(pages)
    append_task_log(database_url, task_id, "切块")
    settings = _embedding_settings()
    if settings is None:
        mark_task_failed(database_url, task_id)
        return
    base_url, api_key, model = settings
    try:
        chunks = [
            (page, content, send_embedding(base_url, api_key, model, content))
            for page, content in pieces
        ]
    except Exception:
        mark_task_failed(database_url, task_id)
        return
    if any(len(vector) != _REQUIRED_DIM for _, _, vector in chunks):
        mark_task_failed(database_url, task_id)
        return
    append_task_log(database_url, task_id, "嵌入")
    store_paper(
        database_url,
        task_id,
        str(task["user_id"]),
        str(task["filename"]),
        str(task["content_sha256"]),
        chunks,
    )


def _extract_pages(pdf: bytes) -> list[tuple[int, str]]:
    """按页抽出正文，页码从 1 起。空白页跳过。"""
    reader = PdfReader(io.BytesIO(pdf))
    pages: list[tuple[int, str]] = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((number, text))
    return pages


def _chunk_pages(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """在每一页内以 400 个字符为窗口、80 个字符重叠切块。"""
    pieces: list[tuple[int, str]] = []
    for number, text in pages:
        if len(text) <= _WINDOW:
            pieces.append((number, text))
            continue
        start = 0
        while True:
            pieces.append((number, text[start : start + _WINDOW]))
            if start + _WINDOW >= len(text):
                break
            start += _STEP
    return pieces


def _embedding_settings() -> tuple[str, str, str] | None:
    """读取嵌入配置。缺失或维度不是 2048 时返回 None，不调用嵌入接口。"""
    base_url = os.environ.get("EMBEDDING_BASE_URL", "").strip()
    api_key = os.environ.get("EMBEDDING_API_KEY", "").strip()
    model = os.environ.get("EMBEDDING_MODEL", "").strip()
    dim = os.environ.get("EMBEDDING_DIM", "").strip()
    if not base_url or not api_key or not model:
        return None
    try:
        if int(dim) != _REQUIRED_DIM:
            return None
    except ValueError:
        return None
    return base_url, api_key, model


def _is_uuid(value: str) -> bool:
    """判断标识是否为 UUID。"""
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
