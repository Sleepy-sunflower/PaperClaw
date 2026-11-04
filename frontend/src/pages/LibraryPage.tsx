import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { clearToken, readToken } from "../auth";

export function LibraryPage(): JSX.Element {
  const token = readToken();
  const navigate = useNavigate();
  const [username, setUsername] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

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

  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (failed) {
    return <p>文献列表没有载入。可能是网络中断。刷新页面再试。</p>;
  }
  if (!username) {
    return <p>正在读取你的文献。</p>;
  }
  return (
    <>
      <p>{username}</p>
      <p>还没有文献。</p>
    </>
  );
}
