import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { App } from "./App";

function LocationProbe(): JSX.Element {
  const location = useLocation();
  return <p data-testid="location">{location.pathname}</p>;
}

function renderAt(path: string): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
      <Routes>
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("user login", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
  });

  test("root without a token opens the bare login page", () => {
    renderAt("/");
    expect(screen.getByTestId("location").textContent).toBe("/login");
    expect(screen.queryByRole("heading", { name: "文献引路" })).toBeNull();
    expect(screen.queryByRole("link", { name: "文献库" })).toBeNull();
    expect(screen.queryByRole("link", { name: "阅读助手" })).toBeNull();
    expect(screen.getByRole("form", { name: "注册" })).toBeTruthy();
    expect(screen.getByRole("form", { name: "登录" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "登出" })).toBeNull();
  });

  test("Scenario: Successful login opens the library", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).endsWith("/api/v1/sessions")) {
          return new Response(
            JSON.stringify({
              code: "ok",
              message: "",
              data: { token: "token-1", username: "reader-one" },
              request_id: "r",
            }),
            { status: 200 },
          );
        }
        return new Response(
          JSON.stringify({
            code: "ok",
            message: "",
            data: { username: "reader-one" },
            request_id: "r",
          }),
          { status: 200 },
        );
      }),
    );
    renderAt("/login");
    expect(screen.getByText("用户名：1 至 32 个字符，只含小写字母、数字和连字符。")).toBeTruthy();
    expect(screen.getByText("密码：1 至 72 个字符。")).toBeTruthy();
    expect(screen.getByRole("form", { name: "注册" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "文献引路" })).toBeNull();
    const form = screen.getByRole("form", { name: "登录" });
    await user.type(form.querySelector('input[name="username"]') as HTMLInputElement, "reader-one");
    await user.type(form.querySelector('input[name="password"]') as HTMLInputElement, "password1");
    await user.click(screen.getByRole("button", { name: "登录" }));
    expect(await screen.findByText("reader-one")).toBeTruthy();
    expect(screen.getByText("还没有文献。")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/library");
    expect(screen.getByRole("heading", { name: "文献引路" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "文献库" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "阅读助手" })).toBeTruthy();
    expect(document.querySelector('input[type="file"]')).toBeNull();
  });

  test("Scenario: Login failure stays on the page", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ code: "unauthenticated" }), { status: 401 })),
    );
    renderAt("/login");
    const form = screen.getByRole("form", { name: "登录" });
    await user.type(form.querySelector('input[name="username"]') as HTMLInputElement, "reader-one");
    await user.type(form.querySelector('input[name="password"]') as HTMLInputElement, "wrong-password");
    await user.click(screen.getByRole("button", { name: "登录" }));
    expect(screen.getByText("登录没有成功。用户名或密码不正确。按上面的规则重新输入后再试。")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/login");
  });

  test("Scenario: Unauthenticated pages go to login", () => {
    const library = renderAt("/library");
    expect(library.getByTestId("location").textContent).toBe("/login");
    expect(library.queryByText("还没有文献。")).toBeNull();
    library.unmount();

    const reader = renderAt("/reader");
    expect(reader.getByTestId("location").textContent).toBe("/login");
    expect(reader.queryByText("还没有提问。")).toBeNull();
  });

  test("Scenario: Click logout from the library", async () => {
    const user = userEvent.setup();
    localStorage.setItem("paperclaw.token", "token-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === "DELETE") {
          return new Response(
            JSON.stringify({ code: "ok", message: "", data: null, request_id: "r" }),
            { status: 200 },
          );
        }
        return new Response(
          JSON.stringify({
            code: "ok",
            message: "",
            data: { username: "reader-one" },
            request_id: "r",
          }),
          { status: 200 },
        );
      }),
    );
    renderAt("/library");
    expect(await screen.findByText("reader-one")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "登出" }));
    expect(await screen.findByRole("form", { name: "登录" })).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/login");
    expect(screen.queryByRole("heading", { name: "文献引路" })).toBeNull();
    expect(screen.queryByRole("link", { name: "文献库" })).toBeNull();
    expect(screen.queryByRole("button", { name: "登出" })).toBeNull();
    expect(localStorage.getItem("paperclaw.token")).toBeNull();
  });

  test("Scenario: Logout stays when the request fails", async () => {
    const user = userEvent.setup();
    const currentUser = new Response(
      JSON.stringify({
        code: "ok",
        message: "",
        data: { username: "reader-one" },
        request_id: "r",
      }),
      { status: 200 },
    );

    localStorage.setItem("paperclaw.token", "token-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === "DELETE") {
          throw new TypeError("network");
        }
        return currentUser.clone();
      }),
    );
    const offline = renderAt("/library");
    expect(await screen.findByText("reader-one")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "登出" }));
    expect(await screen.findByText("登出没有成功。网络可能中断。留在此页再试。")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/library");
    expect(localStorage.getItem("paperclaw.token")).toBe("token-1");
    offline.unmount();

    localStorage.setItem("paperclaw.token", "token-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        if (init?.method === "DELETE") {
          return new Response(JSON.stringify({ code: "unavailable" }), { status: 500 });
        }
        return currentUser.clone();
      }),
    );
    renderAt("/library");
    expect(await screen.findByText("reader-one")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "登出" }));
    expect(await screen.findByText("登出没有成功。网络可能中断。留在此页再试。")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/library");
    expect(localStorage.getItem("paperclaw.token")).toBe("token-1");
  });

  test("Scenario: Login page has no logout", () => {
    renderAt("/login");
    expect(screen.queryByRole("button", { name: "登出" })).toBeNull();
  });
});
