import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { normalizeConfig } from "@smarter.sh/ui-chat";

import { FakeEventSource, installFakes } from "@/mocks/fakes";
import {
  LOG_STREAM_URL,
  MANIFEST_YAML,
  bulkLogs,
  config,
  configWithHistory,
  leanConfig,
  liveLog,
  plainWorkbench,
  workbench,
} from "@/mocks/fixtures";
import { tabHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import Console from "@/components/Console/Component";
import { consoleData } from "@/components/Console/data";
import { MenuItems } from "@/components/Console/enums";

vi.mock("@smarter/manifest-editor", async () => await import("@/mocks/ManifestEditor"));

/** The workbench with the server logs only. */
const logsWorkbench = { ...plainWorkbench, logStreamUrl: LOG_STREAM_URL };

describe("Console", () => {
  it("displays the configuration, then each history that the user selects", async () => {
    const user = userEvent.setup();
    render(<Console workbench={plainWorkbench} config={configWithHistory} />);
    expect(screen.getByRole("button", { name: "Config" })).toHaveAttribute("aria-pressed", "true");
    // the configuration is collapsed to its top-level keys.
    expect(screen.getByText("llmclient")).toBeInTheDocument();
    expect(screen.queryByText("app_name")).not.toBeInTheDocument();
    await user.click(screen.getByText("llmclient"));
    expect(screen.getByText("app_name")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Tool Calls" }));
    expect(screen.getByRole("button", { name: "Tool Calls" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Config" })).toHaveAttribute("aria-pressed", "false");
    // each tool call is collapsed, and named by its function.
    expect(screen.getByText("stackademy_sql")).toBeInTheDocument();
    expect(screen.queryByText("function_name")).not.toBeInTheDocument();
    await user.click(screen.getByText("stackademy_sql"));
    expect(screen.getByText("function_name")).toBeInTheDocument();
  });

  it("names a tool call without a function name", async () => {
    const user = userEvent.setup();
    const history = { ...configWithHistory.history, prompt_tool_call_history: [{ id: 2, prompt: 7 }] };
    render(
      <Console workbench={plainWorkbench} config={{ ...configWithHistory, history } as typeof configWithHistory} />,
    );
    await user.click(screen.getByRole("button", { name: "Tool Calls" }));
    expect(screen.getByText("tool_call")).toBeInTheDocument();
  });

  it("lists Config last, without the optional tabs", () => {
    render(<Console workbench={plainWorkbench} config={configWithHistory} />);
    const labels = screen.getAllByRole("button").map((button) => button.textContent);
    expect(labels).toEqual(["Tool Calls", "Config"]);
  });

  it("lists the server logs before the histories, selects them, and keeps streaming them while another tab is selected", async () => {
    installFakes();
    const user = userEvent.setup();
    render(<Console workbench={logsWorkbench} config={configWithHistory} />);
    const tabs = within(screen.getByRole("navigation", { name: "Console" })).getAllByRole("button");
    expect(tabs.map((button) => button.textContent)).toEqual(["Server Logs", "Tool Calls", "Config"]);
    expect(screen.getByRole("button", { name: "Server Logs" })).toHaveAttribute("aria-pressed", "true");

    const output = screen.getByRole("log", { name: "Console output" });
    expect(output).toHaveTextContent("Connecting to the server log stream...");
    const stream = FakeEventSource.latest();
    // the chat session's own server logs.
    expect(stream.url).toBe(`${LOG_STREAM_URL}?session_key=${configWithHistory.session_key}`);
    act(() => stream.open());
    expect(output).toHaveTextContent("Streaming server logs... There are none yet.");
    act(() => stream.emit(bulkLogs, "bulk"));
    // as the log viewer displays them: their text, which has their time and level, in color.
    expect(output).toHaveTextContent("2026-01-01 12:00:00,000 INFO smarter.apps.prompt prompt started");
    expect(output).toHaveTextContent("2026-01-01 12:00:01,000 WARNING plugin stackademy_sql is slow");
    expect(output).not.toHaveTextContent("\u001b");
    expect(screen.getByText("smarter.apps.prompt")).toHaveStyle("color: #78dce8; font-weight: 700");

    await user.click(screen.getByRole("button", { name: "Config" }));
    act(() => stream.emit(liveLog));
    expect(output).not.toHaveTextContent("prompt finished");
    await user.click(screen.getByRole("button", { name: "Server Logs" }));
    expect(screen.getByText("prompt finished")).toHaveStyle({ color: "#ff8f8f" });
    expect(FakeEventSource.instances).toHaveLength(1);

    act(() => stream.emit({ message: "Waiting for log stream..." }));
    act(() => stream.emit({ message: "no level" }));
    expect(screen.getByText("no level")).toBeInTheDocument();
    expect(output).not.toHaveTextContent("Waiting for log stream...");
    act(() => stream.fail());
    expect(output).toHaveTextContent("The log stream disconnected. Reconnecting...");
    vi.unstubAllGlobals();
  });

  it("lists the manifest first, then the server logs, which it selects, and the deployment last", () => {
    installFakes();
    render(<Console workbench={workbench} config={config} />);
    const tabs = within(screen.getByRole("navigation", { name: "Console" })).getAllByRole("button");
    expect(tabs.map((button) => button.textContent)).toEqual([
      "Manifest",
      "Server Logs",
      "Tool Calls",
      "Config",
      "Deployment",
    ]);
    expect(screen.getByRole("button", { name: "Server Logs" })).toHaveAttribute("aria-pressed", "true");
    vi.unstubAllGlobals();
  });

  it("loads the manifest editor when its tab is selected, and keeps it while another tab is", async () => {
    server.use(...tabHandlers);
    const user = userEvent.setup();
    render(<Console workbench={{ ...plainWorkbench, manifestUrl: workbench.manifestUrl }} config={config} />);
    // not loaded until it is selected.
    expect(screen.queryByLabelText("Manifest YAML")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Manifest" }));
    const editor = await screen.findByLabelText("Manifest YAML");
    expect(editor).toHaveValue(MANIFEST_YAML);
    expect(editor).toBeVisible();
    // hidden, and so not in the accessibility tree.
    expect(screen.queryByRole("log", { name: "Console output" })).not.toBeInTheDocument();

    await user.type(editor, "# unsaved");
    await user.click(screen.getByRole("button", { name: "Config" }));
    expect(editor).not.toBeVisible();
    expect(screen.getByRole("log", { name: "Console output" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Manifest" }));
    // the same editor, with its unsaved changes.
    expect(screen.getByLabelText("Manifest YAML")).toBe(editor);
    expect(editor).toHaveValue(`${MANIFEST_YAML}# unsaved`);
  });

  it("tells its parent when the manifest editor saves the manifest", async () => {
    server.use(...tabHandlers);
    const user = userEvent.setup();
    const onManifestSaved = vi.fn();
    render(
      <Console
        workbench={{ ...plainWorkbench, manifestUrl: workbench.manifestUrl }}
        config={config}
        onManifestSaved={onManifestSaved}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Manifest" }));
    await user.click(await screen.findByRole("button", { name: "Save" }));
    expect(onManifestSaved).toHaveBeenCalledOnce();
  });

  it("loads the deployment page when its tab is selected, and keeps it while another tab is", async () => {
    server.use(...tabHandlers);
    const user = userEvent.setup();
    render(<Console workbench={{ ...plainWorkbench, deploymentUrl: workbench.deploymentUrl }} config={config} />);
    expect(screen.queryByRole("heading", { level: 1 })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Deployment" }));
    const heading = await screen.findByRole("heading", { level: 1, name: "Deployed" });
    expect(screen.getByRole("heading", { name: "Choose its api key" })).toBeInTheDocument();
    expect(screen.queryByRole("log", { name: "Console output" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Config" }));
    expect(heading).not.toBeVisible();
    await user.click(screen.getByRole("button", { name: "Deployment" }));
    expect(screen.getByRole("heading", { level: 1, name: "Deployed" })).toBe(heading);
  });

  it("scrolls long lines, or wraps them, and remembers which", async () => {
    installFakes();
    const user = userEvent.setup();
    const { unmount } = render(<Console workbench={logsWorkbench} config={config} />);
    const toggle = screen.getByRole("button", { name: "Wrap lines" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    unmount();

    render(<Console workbench={logsWorkbench} config={config} />);
    expect(screen.getByRole("button", { name: "Wrap lines" })).toHaveAttribute("aria-pressed", "true");
    vi.unstubAllGlobals();
  });

  it("streams the server logs at its log level, and reconnects when the level changes", () => {
    installFakes();
    const { rerender } = render(<Console workbench={logsWorkbench} config={config} logLevel="DEBUG" />);
    expect(FakeEventSource.latest().url).toBe(`${LOG_STREAM_URL}?level=DEBUG&session_key=${config.session_key}`);
    rerender(<Console workbench={logsWorkbench} config={config} logLevel={null} />);
    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.latest().url).toBe(`${LOG_STREAM_URL}?session_key=${config.session_key}`);
    vi.unstubAllGlobals();
  });

  it("streams the server logs of its chat session only, and a new chat session's from the start", () => {
    installFakes();
    // before the configuration loads, there is no chat session, and no stream.
    const { rerender } = render(<Console workbench={logsWorkbench} config={null} />);
    expect(FakeEventSource.instances).toHaveLength(0);

    rerender(<Console workbench={logsWorkbench} config={config} />);
    const stream = FakeEventSource.latest();
    act(() => stream.open());
    act(() => stream.emit(bulkLogs, "bulk"));
    const output = screen.getByRole("log", { name: "Console output" });
    expect(output).toHaveTextContent("prompt started");

    const newSessionKey = "b".repeat(64);
    rerender(<Console workbench={logsWorkbench} config={{ ...config, session_key: newSessionKey }} />);
    expect(FakeEventSource.latest().url).toBe(`${LOG_STREAM_URL}?session_key=${newSessionKey}`);
    expect(output).not.toHaveTextContent("prompt started");
    vi.unstubAllGlobals();
  });

  it("clears the server logs when its reset key changes", () => {
    installFakes();
    const { rerender } = render(<Console workbench={logsWorkbench} config={config} resetKey={0} />);
    const stream = FakeEventSource.latest();
    act(() => stream.open());
    act(() => stream.emit(bulkLogs, "bulk"));
    const output = screen.getByRole("log", { name: "Console output" });
    expect(output).toHaveTextContent("prompt started");

    rerender(<Console workbench={logsWorkbench} config={config} resetKey={0} />);
    expect(output).toHaveTextContent("prompt started");
    rerender(<Console workbench={logsWorkbench} config={config} resetKey={1} />);
    expect(output).not.toHaveTextContent("prompt started");
    vi.unstubAllGlobals();
  });

  it("says when a history is empty", async () => {
    const user = userEvent.setup();
    render(<Console workbench={plainWorkbench} config={config} />);
    await user.click(screen.getByRole("button", { name: "Tool Calls" }));
    expect(screen.getByText("No tool calls in this chat session yet.")).toBeInTheDocument();
  });

  it("says nothing about a history that the configuration doesn't have yet", async () => {
    const user = userEvent.setup();
    render(<Console workbench={plainWorkbench} config={leanConfig(configWithHistory)} />);
    await user.click(screen.getByRole("button", { name: "Tool Calls" }));
    const output = screen.getByRole("log", { name: "Console output" });
    expect(output).not.toHaveTextContent("No tool calls in this chat session yet.");
    expect(output).not.toHaveTextContent("function_name");
  });

  it("tells its owner which menu item is selected", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<Console workbench={plainWorkbench} config={config} onSelect={onSelect} />);
    expect(onSelect).toHaveBeenLastCalledWith(MenuItems.CHAT_CONFIG);
    await user.click(screen.getByRole("button", { name: "Tool Calls" }));
    expect(onSelect).toHaveBeenLastCalledWith(MenuItems.CHAT_TOOL_CALL_HISTORY);
  });

  it("displays only the shell's prompt before the configuration loads", () => {
    render(<Console workbench={plainWorkbench} config={null} />);
    expect(screen.getByRole("log", { name: "Console output" })).toHaveTextContent(/Last login: .* from 192\.168\./);
  });
});

describe("consoleData", () => {
  it("returns each menu item's data", () => {
    const history = configWithHistory.history;
    expect(consoleData(configWithHistory, MenuItems.CHAT_CONFIG)).toEqual([configWithHistory]);
    expect(consoleData(configWithHistory, MenuItems.CHAT_TOOL_CALL_HISTORY)).toBe(history.prompt_tool_call_history);
  });

  it("returns null for the tool calls of a configuration without them, e.g. without ?verbose=true", () => {
    expect(consoleData(leanConfig(configWithHistory), MenuItems.CHAT_TOOL_CALL_HISTORY)).toBeNull();
  });

  it("reads a version 1 configuration's tool calls, once normalized", () => {
    const { contract: _contract, ...v2 } = configWithHistory;
    const rename = (value: unknown): unknown => {
      if (Array.isArray(value)) return value.map(rename);
      if (!value || typeof value !== "object") return value;
      return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [key.replaceAll("llmclient", "chatbot"), rename(item)]),
      );
    };
    const normalized = normalizeConfig(rename(v2));
    expect(consoleData(normalized, MenuItems.CHAT_TOOL_CALL_HISTORY)).toEqual(
      configWithHistory.history.prompt_tool_call_history,
    );
  });

  it("returns nothing for the tabs that aren't JSON", () => {
    for (const item of [MenuItems.SERVER_LOGS, MenuItems.MANIFEST, MenuItems.DEPLOYMENT]) {
      expect(consoleData(configWithHistory, item)).toEqual([]);
    }
  });

  it("returns nothing before the configuration loads", () => {
    expect(consoleData(null, MenuItems.CHAT_CONFIG)).toEqual([]);
  });
});
