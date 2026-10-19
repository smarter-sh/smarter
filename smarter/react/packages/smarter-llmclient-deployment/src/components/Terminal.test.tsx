import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { COPIED_MILLISECONDS } from "@/components/CopyButton";
import Terminal from "@/components/Terminal";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Terminal", () => {
  it("shows its title and its text, and copies the text", async () => {
    const user = userEvent.setup();
    render(<Terminal title="bash" code="smarter deploy llmclient stackademy" />);
    const terminal = screen.getByRole("group", { name: "bash" });
    expect(terminal).toHaveTextContent("smarter deploy llmclient stackademy");
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(await navigator.clipboard.readText()).toBe("smarter deploy llmclient stackademy");
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("says Copy again after a moment", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<Terminal title="bash" code="x" />);
    await user.click(screen.getByRole("button", { name: "Copy" }));
    // The label changes only once the clipboard write resolves, which can lag the click on a slow runner.
    await user.click(await screen.findByRole("button", { name: "Copied" }));
    act(() => {
      vi.advanceTimersByTime(COPIED_MILLISECONDS);
    });
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  it("shows its children in place of the text, and copies the text", async () => {
    const user = userEvent.setup();
    render(
      <Terminal title="manifest.yaml" code="kind: LLMClient" tall>
        <span>highlighted</span>
      </Terminal>,
    );
    expect(screen.getByText("highlighted")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(await navigator.clipboard.readText()).toBe("kind: LLMClient");
  });

  it("stays as it is if the clipboard refuses", async () => {
    const user = userEvent.setup();
    render(<Terminal title="bash" code="x" />);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
    expect(error).toHaveBeenCalled();
  });
});
