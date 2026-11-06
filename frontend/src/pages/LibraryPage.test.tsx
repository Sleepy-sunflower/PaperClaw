import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { LibraryPage } from "./LibraryPage";

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
        for (const word of ["待处理", "处理中", "已可检索", "抽字", "切块", "嵌入", "写入"]) {
          expect(text).toContain(word);
        }
      },
      { timeout: 3000 },
    );
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
});
