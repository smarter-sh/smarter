import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import ManifestSnippet, { COPIED_MILLISECONDS } from "@/components/ManifestSnippet";
import { GUARDRAIL_SNIPPET } from "@/lib/gettingStarted";

describe("ManifestSnippet", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows the excerpt beneath its context, and copies only the lines to add", async () => {
    const user = userEvent.setup();
    render(<ManifestSnippet snippet={GUARDRAIL_SNIPPET} label="Two built-in Guardrails" />);
    const snippet = screen.getByRole("group", { name: "Two built-in Guardrails" });
    expect(snippet).toHaveTextContent("spec:");
    expect(snippet).toHaveTextContent("pii_redaction_input");
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(await navigator.clipboard.readText()).toBe(`${GUARDRAIL_SNIPPET.code}\n`);
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("says Copy again after a moment", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<ManifestSnippet snippet={GUARDRAIL_SNIPPET} label="x" />);
    await user.click(screen.getByRole("button", { name: "Copy" }));
    await user.click(screen.getByRole("button", { name: "Copied" }));
    act(() => {
      vi.advanceTimersByTime(COPIED_MILLISECONDS);
    });
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  it("stays as it is if the clipboard refuses", async () => {
    const user = userEvent.setup();
    render(<ManifestSnippet snippet={GUARDRAIL_SNIPPET} label="x" />);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(error).toHaveBeenCalled();
  });
});
