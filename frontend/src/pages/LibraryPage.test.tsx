import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { LibraryPage, SESSION_TIMEOUT_MS } from "./LibraryPage";

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(
    JSON.stringify({ code: "ok", message: "", data, request_id: "r" }),
    { status, headers: { "Content-Type": "application/json" } },
  );
}

function renderLibrary(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={["/library"]}>
      <LibraryPage />
    </MemoryRouter>,
  );
}

async function uploadFile(user: ReturnType<typeof userEvent.setup>, name: string): Promise<void> {
  const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
  const file = new File(["%PDF-1.4 in-memory"], name, { type: "application/pdf" });
  await user.upload(fileInput, file);
  await user.click(screen.getByRole("button", { name: "上传" }));
}

describe("paper ingest library", () => {
  beforeEach(() => {
    cleanup();
    localStorage.clear();
    localStorage.setItem("paperclaw.token", "token-1");
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("Scenario: Library shows the task log", async () => {
    const user = userEvent.setup();
    let taskCalls = 0;
    let ready = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const path = String(url);
        if (path.endsWith("/api/v1/sessions/current")) {
          return jsonResponse({ username: "reader-one" });
        }
        if (init?.method === "POST" && path.endsWith("/api/v1/papers")) {
          return jsonResponse({ task_id: "t1", status: "待处理" }, 202);
        }
        if (path.includes("/api/v1/paper-tasks/")) {
          taskCalls += 1;
          if (taskCalls === 1) {
            return jsonResponse({ task_id: "t1", status: "处理中", log: ["抽字", "切块"] });
          }
          ready = true;
          return jsonResponse({
            task_id: "t1",
            status: "已可检索",
            log: ["抽字", "切块", "嵌入", "写入"],
          });
        }
        if (path.endsWith("/api/v1/papers")) {
          return jsonResponse(ready ? [{ id: "p1", filename: "paper.pdf" }] : []);
        }
        return jsonResponse(null);
      }),
    );

    renderLibrary();
    expect(await screen.findByText("reader-one")).toBeTruthy();
    await uploadFile(user, "paper.pdf");

    await waitFor(
      () => {
        const text = document.querySelector("pre")?.textContent ?? "";
        for (const word of ["已可检索", "抽字", "切块", "嵌入", "写入"]) {
          expect(text).toContain(word);
        }
        expect(text.trim()).not.toBe("");
      },
      { timeout: 3000 },
    );
  });

  test("Scenario: Skipped intermediate status does not stall the page", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const path = String(url);
        if (path.endsWith("/api/v1/sessions/current")) {
          return jsonResponse({ username: "reader-one" });
        }
        if (init?.method === "POST" && path.endsWith("/api/v1/papers")) {
          return jsonResponse({ task_id: "t1", status: "待处理" }, 202);
        }
        if (path.includes("/api/v1/paper-tasks/")) {
          return jsonResponse({
            task_id: "t1",
            status: "已可检索",
            log: ["抽字", "切块", "嵌入", "写入"],
          });
        }
        if (path.endsWith("/api/v1/papers")) {
          return jsonResponse([{ id: "p1", filename: "fast-paper.pdf" }]);
        }
        return jsonResponse(null);
      }),
    );

    renderLibrary();
    expect(await screen.findByText("reader-one")).toBeTruthy();
    await uploadFile(user, "fast-paper.pdf");

    await waitFor(
      () => {
        const text = document.querySelector("pre")?.textContent ?? "";
        for (const word of ["已可检索", "抽字", "切块", "嵌入", "写入"]) {
          expect(text).toContain(word);
        }
        expect(text.trim()).not.toBe("");
      },
      { timeout: 3000 },
    );
    expect(await screen.findByText("fast-paper.pdf", {}, { timeout: 3000 })).toBeTruthy();
  });

  test("Scenario: Library shows the uploaded filename", async () => {
    const user = userEvent.setup();
    let ready = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const path = String(url);
        if (path.endsWith("/api/v1/sessions/current")) {
          return jsonResponse({ username: "reader-one" });
        }
        if (init?.method === "POST" && path.endsWith("/api/v1/papers")) {
          return jsonResponse({ task_id: "t1", status: "待处理" }, 202);
        }
        if (path.includes("/api/v1/paper-tasks/")) {
          ready = true;
          return jsonResponse({
            task_id: "t1",
            status: "已可检索",
            log: ["抽字", "切块", "嵌入", "写入"],
          });
        }
        if (path.endsWith("/api/v1/papers")) {
          return jsonResponse(ready ? [{ id: "p1", filename: "my-paper.pdf" }] : []);
        }
        return jsonResponse(null);
      }),
    );

    renderLibrary();
    expect(await screen.findByText("reader-one")).toBeTruthy();
    expect(screen.getByText("还没有文献。")).toBeTruthy();
    await uploadFile(user, "my-paper.pdf");

    expect(await screen.findByText("my-paper.pdf", {}, { timeout: 3000 })).toBeTruthy();
    await waitFor(() => expect(screen.queryByText("还没有文献。")).toBeNull(), { timeout: 3000 });
  });

  test("Scenario: Filename is shown as text", async () => {
    const user = userEvent.setup();
    const odd = 'weird"<b>name</b>.pdf';
    let ready = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const path = String(url);
        if (path.endsWith("/api/v1/sessions/current")) {
          return jsonResponse({ username: "reader-one" });
        }
        if (init?.method === "POST" && path.endsWith("/api/v1/papers")) {
          return jsonResponse({ task_id: "t1", status: "待处理" }, 202);
        }
        if (path.includes("/api/v1/paper-tasks/")) {
          ready = true;
          return jsonResponse({ task_id: "t1", status: "已可检索", log: ["写入"] });
        }
        if (path.endsWith("/api/v1/papers")) {
          return jsonResponse(ready ? [{ id: "p1", filename: odd }] : []);
        }
        return jsonResponse(null);
      }),
    );

    renderLibrary();
    expect(await screen.findByText("reader-one")).toBeTruthy();
    await uploadFile(user, odd);

    await waitFor(
      () => {
        const item = document.querySelector("li");
        expect(item).toBeTruthy();
        expect(item?.textContent).toBe(odd);
      },
      { timeout: 3000 },
    );
    expect(document.querySelector("b")).toBeNull();
  });

  test("Scenario: Library shows an error when the session read times out", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            );
          }),
      ),
    );

    renderLibrary();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(SESSION_TIMEOUT_MS);
    });

    expect(screen.getByText("文献列表没有载入。可能是网络中断。刷新页面再试。")).toBeTruthy();
    expect(screen.queryByText("正在读取你的文献。")).toBeNull();
  });
});
