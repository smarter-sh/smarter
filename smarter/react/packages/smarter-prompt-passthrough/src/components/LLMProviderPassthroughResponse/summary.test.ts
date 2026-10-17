import { describe, expect, it } from "vitest";

import { completion, providerError, toolCallCompletion } from "@/mocks/fixtures";

import {
  completionSummary,
  editorHeight,
  errorSummary,
  formatBytes,
  formatDuration,
} from "@/components/LLMProviderPassthroughResponse/summary";

describe("completionSummary", () => {
  it("reads a chat completion's reply, model, finish reason and token counts", () => {
    expect(completionSummary(completion)).toEqual({
      content: "Hello! How can I help?",
      toolCalls: [],
      model: "gpt-4o-mini-2024-07-18",
      finishReason: "stop",
      usage: { prompt: 13, completion: 7, total: 20 },
    });
  });

  it("reads the tools that the model called", () => {
    expect(completionSummary(toolCallCompletion)).toMatchObject({
      content: null,
      toolCalls: [{ name: "get_current_weather", arguments: '{"location":"San Francisco, CA"}' }],
      finishReason: "tool_calls",
    });
  });

  it("tolerates a choice without a message, a tool call without a function, and missing usage", () => {
    expect(completionSummary({ choices: [{}] })).toEqual({
      content: null,
      toolCalls: [],
      model: null,
      finishReason: null,
      usage: null,
    });
    expect(
      completionSummary({ choices: [{ message: { tool_calls: [{}, "junk"] } }], usage: { total_tokens: "x" } }),
    ).toMatchObject({ toolCalls: [{ name: "?", arguments: "" }], usage: { prompt: 0, completion: 0, total: 0 } });
  });

  it("is null for anything that isn't a chat completion", () => {
    expect(completionSummary(null)).toBeNull();
    expect(completionSummary("text")).toBeNull();
    expect(completionSummary({ choices: [] })).toBeNull();
    expect(completionSummary({ choices: ["x"] })).toBeNull();
  });
});

describe("errorSummary", () => {
  it("reads Smarter's journaled error", () => {
    expect(errorSummary(providerError)).toEqual({
      errorClass: "NotFoundError",
      message: providerError.error.description,
      stacktrace: providerError.error.stacktrace,
    });
  });

  it("reads an error's message, the budget's error, and DRF's detail", () => {
    expect(errorSummary({ error: { message: "Invalid API key" } })).toEqual({
      errorClass: null,
      message: "Invalid API key",
      stacktrace: null,
    });
    expect(errorSummary({ error: {}, message: "outer" })?.message).toBe("outer");
    expect(errorSummary({ error: "budget_exceeded", message: "Over budget" })?.message).toBe("Over budget");
    expect(errorSummary({ error: "budget_exceeded" })?.message).toBe("budget_exceeded");
    expect(errorSummary({ detail: "Not found." })?.message).toBe("Not found.");
  });

  it("is null when the body doesn't describe an error", () => {
    expect(errorSummary("<html></html>")).toBeNull();
    expect(errorSummary([])).toBeNull();
    expect(errorSummary({ error: {} })).toBeNull();
    expect(errorSummary({ ok: false })).toBeNull();
  });
});

describe("formatting", () => {
  it("sizes the editor to its text, within limits", () => {
    expect(editorHeight("{}")).toBe(120);
    expect(editorHeight("\n".repeat(9))).toBe(244);
    expect(editorHeight("\n".repeat(100))).toBe(600);
  });

  it("formats sizes and durations", () => {
    expect(formatBytes(846)).toBe("846 B");
    expect(formatBytes(2176)).toBe("2.1 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
    expect(formatDuration(379.6)).toBe("380 ms");
    expect(formatDuration(1240)).toBe("1.24 s");
  });
});
