import { FormEvent, useCallback, useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { clearToken, readToken } from "../auth";

type Paper = { id: string; filename: string };
type TaskData = { status: string; log: string[] };

const POLL_MS = 400;

export function LibraryPage(): JSX.Element {
  const token = readToken();
  const navigate = useNavigate();
  const [username, setUsername] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    fetch("/api/v1/sessions/current", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (response.status === 401) {
          clearToken();
          navigate("/login");
          return;
        }
        if (!response.ok) {
          if (!cancelled) {
            setFailed(true);
          }
          return;
        }
        const body = (await response.json()) as { data: { username: string } };
        if (!cancelled) {
          setUsername(body.data.username);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, navigate]);

  const loadPapers = useCallback(async (): Promise<void> => {
    if (!token) {
      return;
    }
    try {
      const response = await fetch("/api/v1/papers", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        return;
      }
      const body = (await response.json()) as { data: unknown };
      if (Array.isArray(body.data)) {
        setPapers(body.data as Paper[]);
      }
    } catch {
      // 列表读不到时保持现状
    }
  }, [token]);

  useEffect(() => {
    void loadPapers();
  }, [loadPapers]);

  useEffect(() => {
    if (!token || !taskId) {
      return;
    }
    let cancelled = false;
    let timer = 0;

    async function poll(): Promise<void> {
      try {
        const response = await fetch(`/api/v1/paper-tasks/${taskId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (cancelled) {
          return;
        }
        if (!response.ok) {
          setTaskId(null);
          setError("任务状态没有读到。网络可能中断。留在此页再试。");
          return;
        }
        const body = (await response.json()) as { data: TaskData };
        const data = body.data;
        setStatuses((previous) =>
          previous[previous.length - 1] === data.status
            ? previous
            : [...previous, data.status],
        );
        setLog(data.log);
        if (data.status === "已可检索") {
          setTaskId(null);
          void loadPapers();
          return;
        }
        if (data.status === "失败") {
          setTaskId(null);
          setError("处理没有成功。这份文献没有入库。检查后再传一次。");
          return;
        }
        timer = window.setTimeout(poll, POLL_MS);
      } catch {
        if (!cancelled) {
          setTaskId(null);
          setError("任务状态没有读到。网络可能中断。留在此页再试。");
        }
      }
    }

    void poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [token, taskId, loadPapers]);

  async function onUpload(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) {
      return;
    }
    const input = event.currentTarget.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement | null;
    const picked = input?.files?.[0];
    if (!picked) {
      return;
    }
    setError("");
    const form = new FormData();
    form.append("file", picked);
    let response: Response;
    try {
      response = await fetch("/api/v1/papers", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
    } catch {
      setError("上传没有成功。网络可能中断。留在此页再试。");
      return;
    }
    if (response.status !== 202) {
      setError("上传没有成功。只接受不超过 20MB 的 PDF。换一份文件再试。");
      return;
    }
    const body = (await response.json()) as { data: { task_id: string; status: string } };
    setStatuses([body.data.status]);
    setLog([]);
    setTaskId(body.data.task_id);
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (failed) {
    return <p>文献列表没有载入。可能是网络中断。刷新页面再试。</p>;
  }
  if (!username) {
    return <p>正在读取你的文献。</p>;
  }
  const hasTaskText = statuses.length > 0;
  return (
    <>
      <p>{username}</p>
      <form aria-label="上传" onSubmit={onUpload}>
        <input type="file" name="file" accept="application/pdf" />
        <button type="submit">上传</button>
      </form>
      {hasTaskText ? <pre>{[...statuses, ...log].join("\n")}</pre> : null}
      {error ? <p>{error}</p> : null}
      {papers.length === 0 ? (
        <p>还没有文献。</p>
      ) : (
        <ul>
          {papers.map((paper) => (
            <li key={paper.id}>{paper.filename}</li>
          ))}
        </ul>
      )}
    </>
  );
}
