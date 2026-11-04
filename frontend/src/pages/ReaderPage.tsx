import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { clearToken, readToken } from "../auth";

export function ReaderPage(): JSX.Element {
  const token = readToken();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    fetch("/api/v1/sessions/current", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((response) => {
        if (cancelled) {
          return;
        }
        if (response.status === 401) {
          clearToken();
          navigate("/login");
          return;
        }
        if (!response.ok) {
          setFailed(true);
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
    return <p>阅读助手没有载入。可能是网络中断。刷新页面再试。</p>;
  }
  return <p>还没有提问。</p>;
}
