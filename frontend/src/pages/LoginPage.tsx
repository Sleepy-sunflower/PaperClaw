import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { saveToken } from "../auth";

type Status = "idle" | "loading" | "error";

export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const [loginStatus, setLoginStatus] = useState<Status>("idle");
  const [registerStatus, setRegisterStatus] = useState<Status>("idle");
  const [registerError, setRegisterError] = useState("");

  async function onLogin(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setLoginStatus("loading");
    const response = await fetch("/api/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: form.get("username"),
        password: form.get("password"),
      }),
    });
    if (!response.ok) {
      setLoginStatus("error");
      return;
    }
    const body = (await response.json()) as { data: { token: string } };
    saveToken(body.data.token);
    navigate("/library");
  }

  async function onRegister(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setRegisterStatus("loading");
    setRegisterError("");
    const response = await fetch("/api/v1/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: form.get("username"),
        password: form.get("password"),
      }),
    });
    if (!response.ok) {
      const body = (await response.json()) as { code?: string };
      setRegisterStatus("error");
      setRegisterError(
        body.code === "already_exists"
          ? "注册没有成功。这个用户名已经有人使用。换一个用户名再试。"
          : "注册没有成功。用户名或密码不符合要求。按上面的规则修改后再试。",
      );
      return;
    }
    setRegisterStatus("idle");
  }

  return (
    <>
      <p>用户名：1 至 32 个字符，只含小写字母、数字和连字符。</p>
      <p>密码：1 至 72 个字符。</p>
      <form aria-label="注册" onSubmit={onRegister}>
        <label>
          用户名
          <input name="username" />
        </label>
        <label>
          密码
          <input name="password" type="password" />
        </label>
        <button type="submit">注册</button>
        {registerStatus === "loading" ? <p>正在注册。</p> : null}
        {registerStatus === "error" ? <p>{registerError}</p> : null}
      </form>
      <form aria-label="登录" onSubmit={onLogin}>
        <label>
          用户名
          <input name="username" />
        </label>
        <label>
          密码
          <input name="password" type="password" />
        </label>
        <button type="submit">登录</button>
        {loginStatus === "loading" ? <p>正在登录。</p> : null}
        {loginStatus === "error" ? (
          <p>登录没有成功。用户名或密码不正确。按上面的规则重新输入后再试。</p>
        ) : null}
      </form>
    </>
  );
}
