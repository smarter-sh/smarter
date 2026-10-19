/* eslint-disable testing-library/no-node-access -- the lines, and the viewer's modes, have no roles: they are divs, and css classes. */
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { stripAnsi } from "@/lib/ansi";
import { LOG_WRAP_STORAGE_KEY } from "@/lib/layout";
import { bulkLogs, liveLog } from "@/mocks/fixtures";

import ServerLogs from "@/components/Console/ServerLogs";

const logs = [...bulkLogs, liveLog];

function setup(props: Partial<Parameters<typeof ServerLogs>[0]> = {}) {
  render(<ServerLogs logs={logs} connected error={null} {...props} />);
  return userEvent.setup();
}

const lines = () => screen.getByRole("log", { name: "Server logs" });
const root = () => lines().parentElement!;

/** Gives the lines a size, which jsdom doesn't lay out, so that they can scroll. */
function sizeLines(size = { scrollHeight: 1000, clientHeight: 100, scrollWidth: 800 }) {
  for (const [name, value] of Object.entries(size)) {
    Object.defineProperty(lines(), name, { configurable: true, value });
  }
  for (const name of ["scrollTop", "scrollLeft"]) {
    Object.defineProperty(lines(), name, { configurable: true, writable: true, value: 0 });
  }
}

describe("ServerLogs", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("shows each record's text, without its ANSI escape codes, in its colors", () => {
    setup();
    expect(lines().children).toHaveLength(3);
    expect(lines()).toHaveTextContent("prompt started");
    expect(lines()).not.toHaveTextContent("\u001b");
    expect(screen.getByText("smarter.apps.prompt")).toHaveStyle("color: #78dce8; font-weight: 700");
    expect(screen.getByRole("status")).toHaveTextContent("Streaming server logs...");
  });

  it("collapses blocks of JSON, and expands them one by one, or all of them", async () => {
    const message = 'chat_response request: {\n  "model": "gpt",\n  "messages": [\n    "hi"\n  ]\n}\ndone';
    const user = setup({ logs: [{ message }, { message: "a plain line" }] });
    // collapsed: the block's first line, a summary, and the lines after it.
    expect(lines()).toHaveTextContent("chat_response request: {+ … } (4 lines) done");
    expect(lines()).not.toHaveTextContent('"model"');
    expect(lines()).toHaveTextContent("a plain line");

    await user.click(screen.getByRole("button", { name: "Expand the JSON" }));
    expect(lines()).toHaveTextContent('"model": "gpt"');
    // a nested block is collapsed too.
    expect(lines()).toHaveTextContent('"messages": [+ … ] (1 line)');
    await user.click(screen.getByRole("button", { name: "Collapse the JSON" }));
    expect(lines()).not.toHaveTextContent('"model"');

    const expandAll = screen.getByRole("button", { name: "Expand JSON" });
    await user.click(expandAll);
    expect(expandAll).toHaveAttribute("aria-pressed", "true");
    expect(lines()).toHaveTextContent('"hi"');
    expect(screen.queryByRole("button", { name: "Expand the JSON" })).not.toBeInTheDocument();
    await user.click(expandAll);
    expect(lines()).not.toHaveTextContent('"model"');
  });

  it("copies a collapsed block of JSON in full", async () => {
    const message = 'request: {\n  "model": "gpt"\n}';
    // after userEvent.setup(), which installs its own clipboard.
    setup({ logs: [{ message }] });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    fireEvent.click(screen.getByRole("button", { name: "Copy the lines" }));
    expect(writeText).toHaveBeenCalledWith(message);
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("hides the stream's own status messages", () => {
    setup({ logs: [{ message: "Waiting for log stream..." }, { message: "[stream] connected " }] });
    expect(lines().children).toHaveLength(0);
    expect(screen.getByRole("status")).toHaveTextContent("Streaming server logs... There are none yet.");
  });

  it("shows the stream's state: idle, connecting, or disconnected", () => {
    const { rerender } = render(<ServerLogs logs={[]} connected={false} error={null} idleText="Send a request." />);
    expect(screen.getByRole("status")).toHaveTextContent("Send a request.");
    rerender(<ServerLogs logs={[]} connected={false} error={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("Connecting to the server log stream...");
    rerender(<ServerLogs logs={[]} connected={false} error="Disconnected." />);
    expect(screen.getByRole("status")).toHaveTextContent("Disconnected.");
  });

  it("scrolls long lines, or wraps them with the button or w, and remembers which", async () => {
    const user = setup();
    const wrap = screen.getByRole("button", { name: "Wrap lines" });
    expect(wrap).toHaveAttribute("aria-pressed", "false");
    expect(root()).not.toHaveClass("console-server-logs-wrap");

    await user.click(wrap);
    expect(wrap).toHaveAttribute("aria-pressed", "true");
    expect(root()).toHaveClass("console-server-logs-wrap");
    expect(window.localStorage.getItem(LOG_WRAP_STORAGE_KEY)).toBe("true");

    fireEvent.keyDown(lines(), { key: "w" });
    expect(root()).not.toHaveClass("console-server-logs-wrap");
    expect(window.localStorage.getItem(LOG_WRAP_STORAGE_KEY)).toBe("false");
  });

  it("wraps as the user last chose", () => {
    window.localStorage.setItem(LOG_WRAP_STORAGE_KEY, "true");
    setup();
    expect(root()).toHaveClass("console-server-logs-wrap");
  });

  it("works without storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    setup();
    fireEvent.keyDown(lines(), { key: "w" });
    expect(root()).toHaveClass("console-server-logs-wrap");
  });

  it("moves to the top and the bottom with Ctrl+Up and Ctrl+Down, and scrolls by line, page and column", () => {
    setup();
    sizeLines();
    const element = lines();

    fireEvent.keyDown(element, { key: "ArrowUp", ctrlKey: true });
    expect(element.scrollTop).toBe(0);
    expect(screen.getByRole("button", { name: "Follow" })).toHaveAttribute("aria-pressed", "false");

    fireEvent.keyDown(element, { key: "ArrowDown" });
    expect(element.scrollTop).toBe(18);
    fireEvent.keyDown(element, { key: "ArrowUp" });
    expect(element.scrollTop).toBe(0);
    fireEvent.keyDown(element, { key: "PageDown" });
    expect(element.scrollTop).toBe(82);
    fireEvent.keyDown(element, { key: "PageUp" });
    expect(element.scrollTop).toBe(0);

    fireEvent.keyDown(element, { key: "ArrowRight" });
    expect(element.scrollLeft).toBe(40);
    fireEvent.keyDown(element, { key: "ArrowLeft" });
    expect(element.scrollLeft).toBe(0);
    fireEvent.keyDown(element, { key: "ArrowRight", metaKey: true });
    expect(element.scrollLeft).toBe(800);
    fireEvent.keyDown(element, { key: "ArrowLeft", ctrlKey: true });
    expect(element.scrollLeft).toBe(0);

    fireEvent.keyDown(element, { key: "ArrowDown", ctrlKey: true });
    expect(element.scrollTop).toBe(1000);
    expect(screen.getByRole("button", { name: "Follow" })).toHaveAttribute("aria-pressed", "true");
  });

  it("leaves other keys, such as Ctrl+C, to the browser", () => {
    setup();
    expect(fireEvent.keyDown(lines(), { key: "c", ctrlKey: true })).toBe(true);
    expect(fireEvent.keyDown(lines(), { key: "w" })).toBe(false);
  });

  it("follows new records until the user scrolls up, or presses s, and again at the bottom", () => {
    const { rerender } = render(<ServerLogs logs={bulkLogs} connected error={null} />);
    sizeLines();
    rerender(<ServerLogs logs={logs} connected error={null} />);
    expect(lines().scrollTop).toBe(1000);

    lines().scrollTop = 500;
    fireEvent.scroll(lines());
    const follow = screen.getByRole("button", { name: "Follow" });
    expect(follow).toHaveAttribute("aria-pressed", "false");
    rerender(<ServerLogs logs={[...logs, { message: "newer" }]} connected error={null} />);
    expect(lines().scrollTop).toBe(500);

    fireEvent.keyDown(lines(), { key: "s" });
    expect(follow).toHaveAttribute("aria-pressed", "true");
    expect(lines().scrollTop).toBe(1000);
    fireEvent.keyDown(lines(), { key: "s" });
    expect(follow).toHaveAttribute("aria-pressed", "false");

    lines().scrollTop = 900;
    fireEvent.scroll(lines());
    expect(follow).toHaveAttribute("aria-pressed", "true");
  });

  it("follows again with the Follow button", async () => {
    const user = setup();
    sizeLines();
    fireEvent.keyDown(lines(), { key: "g" });
    const follow = screen.getByRole("button", { name: "Follow" });
    await user.click(follow);
    expect(follow).toHaveAttribute("aria-pressed", "true");
    expect(lines().scrollTop).toBe(1000);
    await user.click(follow);
    expect(follow).toHaveAttribute("aria-pressed", "false");
  });

  it("filters the lines with /, and clears the filter with Esc", async () => {
    const user = setup();
    fireEvent.keyDown(lines(), { key: "/" });
    const filter = screen.getByRole("searchbox", { name: "Filter the server logs" });
    expect(filter).toHaveFocus();

    await user.type(filter, "FINISHED");
    expect(lines().children).toHaveLength(1);
    expect(lines()).toHaveTextContent("prompt finished");
    expect(screen.getByRole("status")).toHaveTextContent("1 of 3 lines match.");

    await user.keyboard("{Enter}");
    expect(lines()).toHaveFocus();
    expect(filter).toHaveValue("FINISHED");

    await user.click(filter);
    await user.keyboard("{Escape}");
    expect(filter).toHaveValue("");
    expect(lines()).toHaveFocus();
    expect(lines().children).toHaveLength(3);

    await user.type(filter, "stackademy");
    fireEvent.keyDown(lines(), { key: "Escape" });
    expect(filter).toHaveValue("");
  });

  it("copies the lines that it shows, as plain text, with the button or c", async () => {
    // after userEvent.setup(), which installs its own clipboard.
    setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    fireEvent.keyDown(lines(), { key: "c" });
    expect(writeText).toHaveBeenCalledWith(logs.map((log) => stripAnsi(log.message)).join("\n"));
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();

    writeText.mockRejectedValueOnce(new Error("denied"));
    fireEvent.click(screen.getByRole("button", { name: "Copied" }));
    await vi.waitFor(() => expect(writeText).toHaveBeenCalledTimes(2));
  });

  it("goes full screen with F or its button, and leaves it with Esc", async () => {
    const user = setup();
    fireEvent.keyDown(lines(), { key: "F", shiftKey: true });
    expect(root()).toHaveClass("console-server-logs-fullscreen");
    fireEvent.keyDown(lines(), { key: "Escape" });
    expect(root()).not.toHaveClass("console-server-logs-fullscreen");

    await user.click(screen.getByRole("button", { name: "Full screen" }));
    expect(root()).toHaveClass("console-server-logs-fullscreen");
  });

  it("lists its keyboard shortcuts with ? or its button, and hides them with Esc", async () => {
    const user = setup();
    fireEvent.keyDown(lines(), { key: "?", shiftKey: true });
    const help = screen.getByText("Top").closest("dl")!;
    expect(help).toHaveTextContent("Ctrl+↑");
    expect(help).toHaveTextContent("Top");
    expect(help).toHaveTextContent("Wrap long lines, or scroll them");
    fireEvent.keyDown(lines(), { key: "Escape" });
    expect(screen.queryByText("Wrap long lines, or scroll them")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Keyboard shortcuts" }));
    expect(screen.getByText("Leave full screen, hide the shortcuts, or clear the filter")).toBeInTheDocument();
  });
});
