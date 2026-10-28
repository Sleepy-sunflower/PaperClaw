import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, test } from "vitest";
import { App } from "./App";

function renderAt(path: string): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("shell", () => {
  test("root shows the product name and two entries", () => {
    renderAt("/");
    expect(screen.getByText("文献引路")).toBeTruthy();
    expect(screen.getByText("文献库")).toBeTruthy();
    expect(screen.getByText("阅读助手")).toBeTruthy();
  });

  test("Scenario: Open either entry", () => {
    const library = renderAt("/library");
    expect(library.container.querySelector('input[type="file"]')).toBeNull();
    expect(library.container.querySelector("textarea")).toBeNull();
    expect(library.getByText("还没有文献。")).toBeTruthy();
    library.unmount();

    const reader = renderAt("/reader");
    expect(reader.container.querySelector('input[type="file"]')).toBeNull();
    expect(reader.container.querySelector("textarea")).toBeNull();
    expect(reader.getByText("还没有提问。")).toBeTruthy();
  });
});
