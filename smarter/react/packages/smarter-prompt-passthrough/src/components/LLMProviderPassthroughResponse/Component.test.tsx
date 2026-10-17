import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { completion, providerError, toolCallCompletion } from "@/mocks/fixtures";

import LLMProviderPassthroughResponse from "@/components/LLMProviderPassthroughResponse/Component";
import type { PassthroughResponse } from "@/components/LLMProviderPassthroughResponse/summary";

vi.mock("@monaco-editor/react", async () => await import("@/mocks/MonacoEditor"));

const ok = (body: unknown): PassthroughResponse => ({
  status: 200,
  statusText: "OK",
  body,
  elapsedMs: 1240,
  size: 846,
});

describe("LLMProviderPassthroughResponse", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("says how to get a response before the first one", () => {
    render(<LLMProviderPassthroughResponse apiResponse={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("No response yet");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows a spinner while a request is on its way, rather than the last response", () => {
    render(<LLMProviderPassthroughResponse apiResponse={ok(completion)} isProcessing />);
    expect(screen.getByRole("status")).toHaveTextContent("Waiting for the provider's response…");
    expect(screen.queryByRole("region", { name: "Reply" })).not.toBeInTheDocument();
  });

  it("shows the status, timing, size, reply and raw JSON of a completion", () => {
    render(<LLMProviderPassthroughResponse apiResponse={ok(completion)} />);

    expect(screen.getByText("200 OK")).toHaveClass("badge-light-success");
    expect(screen.getByRole("img", { name: "success" })).toBeInTheDocument();
    expect(screen.getByTitle("Time to respond")).toHaveTextContent("1.24 s");
    expect(screen.getByTitle("Response size")).toHaveTextContent("846 B");

    const reply = screen.getByRole("region", { name: "Reply" });
    expect(reply).toHaveTextContent("Hello! How can I help?");
    expect(within(reply).getByText("gpt-4o-mini-2024-07-18")).toBeInTheDocument();
    expect(within(reply).getByText("stop")).toBeInTheDocument();
    expect(within(reply).getByText("13 prompt · 7 completion · 20 total")).toBeInTheDocument();

    const json = screen.getByLabelText("Response JSON");
    expect(json).toHaveValue(JSON.stringify(completion, null, 2));
    expect(json).toHaveAttribute("readonly");
  });

  it("shows the tools that the model called", () => {
    render(<LLMProviderPassthroughResponse apiResponse={ok(toolCallCompletion)} />);
    const calls = screen.getByRole("list", { name: "Tool calls" });
    expect(calls).toHaveTextContent('get_current_weather({"location":"San Francisco, CA"})');
  });

  it("says when a reply is empty, and leaves out the stats that it doesn't have", () => {
    render(<LLMProviderPassthroughResponse apiResponse={ok({ choices: [{ message: { content: "" } }] })} />);
    expect(screen.getByText("The reply is empty.")).toBeInTheDocument();
    expect(screen.queryByText("Model")).not.toBeInTheDocument();
    expect(screen.queryByText("Tokens")).not.toBeInTheDocument();
  });

  it("shows a success that isn't a completion as raw JSON only", () => {
    render(<LLMProviderPassthroughResponse apiResponse={ok({ data: [] })} />);
    expect(screen.queryByRole("region", { name: "Reply" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Response JSON")).toHaveValue('{\n  "data": []\n}');
  });

  it("shows Smarter's error, with its class and folded stack trace", () => {
    render(
      <LLMProviderPassthroughResponse
        apiResponse={{ status: 400, statusText: "Bad Request", body: providerError, elapsedMs: 380, size: 2176 }}
      />,
    );

    expect(screen.getByText("400 Bad Request")).toHaveClass("badge-light-danger");
    expect(screen.getByRole("img", { name: "failure" })).toBeInTheDocument();
    expect(screen.getByTitle("Time to respond")).toHaveTextContent("380 ms");
    expect(screen.getByTitle("Response size")).toHaveTextContent("2.1 KB");
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText("NotFoundError")).toBeInTheDocument();
    expect(alert).toHaveTextContent("The model `no-such-model` does not exist");
    expect(within(alert).getByText("Stack trace")).toBeInTheDocument();
  });

  it("shows a status without its reason phrase, and a network error", () => {
    const { rerender } = render(
      <LLMProviderPassthroughResponse apiResponse={{ ...ok({}), status: 500, statusText: "" }} />,
    );
    expect(screen.getByText("500")).toHaveClass("badge-light-danger");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    rerender(
      <LLMProviderPassthroughResponse
        apiResponse={{
          status: 0,
          statusText: "",
          body: { error: { message: "Failed to fetch" } },
          elapsedMs: 3,
          size: 0,
        }}
      />,
    );
    expect(screen.getByText("Network error")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Failed to fetch");
  });

  it("shows a body that isn't JSON as it is, and says so", () => {
    render(
      <LLMProviderPassthroughResponse
        apiResponse={{ status: 502, statusText: "Bad Gateway", body: "<h1>502</h1>", elapsedMs: 30012, size: 12 }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("The response isn't JSON.");
    expect(screen.getByText("Raw response")).toBeInTheDocument();
    expect(screen.getByLabelText("Response JSON")).toHaveValue("<h1>502</h1>");
  });

  it("copies the JSON, and says so for a moment", async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    render(<LLMProviderPassthroughResponse apiResponse={ok(completion)} />);

    await user.click(screen.getByRole("button", { name: "Copy JSON" }));
    expect(writeText).toHaveBeenCalledWith(JSON.stringify(completion, null, 2));
    expect(screen.getByRole("button", { name: "Copied to clipboard" })).toBeInTheDocument();

    expect(await screen.findByRole("button", { name: "Copy JSON" }, { timeout: 3000 })).toBeInTheDocument();
  });

  it("logs a copy that the browser refuses", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("denied"));
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<LLMProviderPassthroughResponse apiResponse={ok(completion)} />);

    await user.click(screen.getByRole("button", { name: "Copy JSON" }));
    expect(error).toHaveBeenCalledWith(expect.anything(), "Couldn't copy the response:", expect.any(Error));
    expect(screen.getByRole("button", { name: "Copy JSON" })).toBeInTheDocument();
  });

  it("downloads the JSON as response.json", async () => {
    const user = userEvent.setup();
    URL.createObjectURL = vi.fn(() => "blob:response");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe("response.json");
      expect(this.href).toBe("blob:response");
    });
    render(<LLMProviderPassthroughResponse apiResponse={ok(completion)} />);

    await user.click(screen.getByRole("button", { name: "Download" }));
    expect(click).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:response");
  });

  it("pops the success emoji in, a moment after the response", () => {
    vi.useFakeTimers();
    render(<LLMProviderPassthroughResponse apiResponse={ok(completion)} />);
    const emoji = screen.getByRole("img", { name: "success" });
    expect(emoji).not.toHaveClass("emoji-animate--show");
    act(() => vi.advanceTimersByTime(300));
    expect(emoji).toHaveClass("emoji-animate--show");
  });
});
