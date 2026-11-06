"""只读地查看 Compose 栈数据库里的内容。

用法（仓库根目录）：

    python tools/db_inspect.py
    python tools/db_inspect.py --project paperclaw-e2e --env-file tests/e2e-compose.env

它通过 `docker compose exec -T db psql` 读取，用户名和库名由容器内的环境变量展开，
所以既不需要数据库对宿主机开放端口，也不读取本机 .env。输出打印到标准输出，
同时写进 tmp/db-inspect.txt（Windows 控制台默认编码会把中文显示成乱码）。

只显示白名单字段：不显示 password_hash、token_hash、PDF 字节和向量数值。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "tmp" / "db-inspect.txt"
CHUNK_ROW_LIMIT = 200
PREVIEW_CHARS = 120

PSQL = 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "\t"'

QUERIES: tuple[tuple[str, str, str, str], ...] = (
    (
        "用户",
        "还没有用户。",
        "SELECT username, to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') "
        "FROM users ORDER BY created_at, username",
        "个",
    ),
    (
        "会话",
        "还没有会话。",
        "SELECT users.username, to_char(sessions.created_at, 'YYYY-MM-DD HH24:MI:SS') "
        "FROM sessions JOIN users ON users.id = sessions.user_id "
        "ORDER BY sessions.created_at",
        "条",
    ),
    (
        "文献",
        "还没有文献。",
        "SELECT papers.filename, users.username, left(papers.content_sha256, 12), "
        "(SELECT count(*) FROM chunks WHERE chunks.paper_id = papers.id), "
        "to_char(papers.created_at, 'YYYY-MM-DD HH24:MI:SS') "
        "FROM papers JOIN users ON users.id = papers.user_id "
        "ORDER BY papers.created_at",
        "份",
    ),
    (
        "入库任务",
        "还没有入库任务。",
        "SELECT ingest_tasks.filename, users.username, ingest_tasks.status, "
        "array_to_string(ingest_tasks.log, ' → '), "
        "to_char(ingest_tasks.created_at, 'YYYY-MM-DD HH24:MI:SS') "
        "FROM ingest_tasks JOIN users ON users.id = ingest_tasks.user_id "
        "ORDER BY ingest_tasks.created_at",
        "条",
    ),
    (
        "片段",
        "还没有片段。",
        "SELECT papers.filename, chunks.page, "
        "substr(regexp_replace(chunks.content, E'[\\n\\r\\t|]+', ' ', 'g'), 1, "
        f"{PREVIEW_CHARS}), vector_dims(chunks.embedding) "
        "FROM chunks JOIN papers ON papers.id = chunks.paper_id "
        "ORDER BY papers.filename, chunks.page, chunks.ctid "
        f"LIMIT {CHUNK_ROW_LIMIT}",
        "条",
    ),
)


def compose_command(project: str, env_file: str) -> list[str]:
    """拼出指向目标栈的 docker compose 前缀。"""
    command = ["docker", "compose"]
    if project:
        command += ["-p", project]
    if env_file:
        command += ["--env-file", env_file]
    return command


def run_sql(command: list[str], sql: str) -> tuple[bool, str, str]:
    """把 SQL 从标准输入交给容器里的 psql，避免引号转义问题。"""
    result = subprocess.run(
        [*command, "exec", "-T", "db", "sh", "-c", PSQL],
        input=sql,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0, result.stdout, result.stderr


def rows_of(command: list[str], sql: str) -> tuple[list[list[str]] | None, str]:
    """执行一条查询，返回按制表符切开的行；失败时返回错误摘要。"""
    ok, out, err = run_sql(command, sql)
    if not ok:
        detail = err.strip().splitlines()
        return None, detail[-1] if detail else "psql 没有给出原因"
    return [line.split("\t") for line in out.splitlines() if line], ""


def render_user(row: list[str]) -> str:
    return f"{row[0]}（创建于 {row[1]}）"


def render_session(row: list[str]) -> str:
    return f"{row[0]} 的会话（创建于 {row[1]}）"


def render_paper(row: list[str]) -> str:
    return f"{row[0]}，属于 {row[1]}，{row[3]} 个片段，sha256 前 12 位 {row[2]}（创建于 {row[4]}）"


def render_task(row: list[str]) -> str:
    return f"{row[0]}，属于 {row[1]}，状态 {row[2]}，日志 {row[3] or '（空）'}（创建于 {row[4]}）"


def render_chunk(row: list[str]) -> str:
    return f"[{row[0]} 第 {row[1]} 页，向量 {row[3]} 维] {row[2]}"


RENDERERS = (render_user, render_session, render_paper, render_task, render_chunk)


def build_report(command: list[str], project: str, env_file: str) -> tuple[str, int]:
    """读出每一节并拼成一份纯文本报告。返回报告文本和退出码。"""
    lines = [
        "数据库内容",
        f"Compose 项目：{project or '（当前目录的默认项目）'}",
        f"环境变量文件：{env_file or '（未指定）'}",
    ]

    ok, _, err = run_sql(command, "SELECT 1")
    if not ok:
        detail = err.strip().splitlines()
        reason = detail[-1] if detail else "docker compose exec 没有成功"
        return (
            "\n".join(
                [
                    "数据库读不到，所以这次没有输出内容。",
                    f"原因：{reason}",
                    "请先运行 docker compose up -d 并等数据库就绪；"
                    "如果改过 POSTGRES_PASSWORD，卷里的口令仍是旧的，"
                    "需要 docker compose down -v（会清空数据）或在容器里执行 ALTER ROLE。",
                ]
            )
            + "\n",
            1,
        )

    for index, ((title, empty_text, sql, unit), render) in enumerate(zip(QUERIES, RENDERERS)):
        rows, error = rows_of(command, sql)
        lines.append("")
        if rows is None:
            lines.append(f"{title}：读不到这一节。原因：{error}")
            continue
        lines.append(f"{title}（共 {len(rows)} {unit}）")
        if not rows:
            lines.append(f"  {empty_text}")
            continue
        lines.extend(f"  {render(row)}" for row in rows)
        if index == len(QUERIES) - 1 and len(rows) == CHUNK_ROW_LIMIT:
            lines.append(f"  （只显示前 {CHUNK_ROW_LIMIT} 条，库里可能还有更多）")

    return "\n".join(lines) + "\n", 0


def main() -> int:
    """解析参数、生成报告、打印并写入文件，返回退出码。"""
    parser = argparse.ArgumentParser(description="只读地查看数据库里的用户、文献和片段内容。")
    parser.add_argument("--project", default="", help="Compose 项目名，默认使用当前目录的默认项目")
    parser.add_argument("--env-file", default="", help="Compose 环境变量文件，默认不指定")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="报告写入的文件路径")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    report, exit_code = build_report(
        compose_command(args.project, args.env_file), args.project, args.env_file
    )
    print(report, end="")

    output = Path(args.output)
    if exit_code == 0:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"报告已写入 {output}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
