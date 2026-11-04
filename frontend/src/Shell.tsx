import { useState } from "react";
import { Link, Navigate, Outlet, useNavigate } from "react-router-dom";
import { clearToken, readToken } from "./auth";

export function Shell(): JSX.Element {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const token = readToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  async function onLogout(): Promise<void> {
    setError("");
    try {
      const response = await fetch("/api/v1/sessions/current", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status !== 200 && response.status !== 401) {
        setError("登出没有成功。网络可能中断。留在此页再试。");
        return;
      }
    } catch {
      setError("登出没有成功。网络可能中断。留在此页再试。");
      return;
    }
    clearToken();
    navigate("/login");
  }

  return (
    <>
      <h1>文献引路</h1>
      <nav>
        <Link to="/library">文献库</Link>
        <br />
        <Link to="/reader">阅读助手</Link>
        <br />
        <button type="button" onClick={onLogout}>
          登出
        </button>
        {error ? <p>{error}</p> : null}
      </nav>
      <Outlet />
    </>
  );
}
