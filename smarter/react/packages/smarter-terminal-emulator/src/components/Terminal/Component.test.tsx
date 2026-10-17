import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FakeSerializeAddon, FakeTerminal, FakeWebSocket, installFakes, written } from "@/mocks/fakes";
import { SCREEN_KEY } from "@/lib/screen";
import { sessionContext, sessionMessage } from "@/mocks/fixtures";
import { ticketHandlers, ticketRefusedHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

import TerminalEmulator from "@/components/Terminal/Component";

vi.mock("@xterm/xterm", async () => ({ Terminal: (await import("@/mocks/fakes")).FakeTerminal }));
vi.mock("@xterm/addon-fit", async () => ({ FitAddon: (await import("@/mocks/fakes")).FakeFitAddon }));
vi.mock("@xterm/addon-serialize", async () => ({
  SerializeAddon: (await import("@/mocks/fakes")).FakeSerializeAddon,
}));
vi.mock("@xterm/xterm/css/xterm.css", () => ({}));

/** The terminal that connect() rendered last, to unmount it, as when the page is left. */
let rendered: ReturnType<typeof render>;

/** Render the terminal, and wait for its WebSocket. */
async function connect(): Promise<FakeWebSocket> {
  rendered = render(<TerminalEmulator sessionContext={sessionContext} />);
  await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(1));
  const socket = FakeWebSocket.latest();
  socket.open();
  return socket;
}

const output = () => written.join("");

describe("TerminalEmulator", () => {
  beforeEach(() => {
    installFakes();
    server.use(...ticketHandlers);
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("opens the WebSocket with the ticket and the terminal's size, and focuses the terminal", async () => {
    const socket = await connect();
    const url = new URL(socket.url);
    expect(url.protocol).toBe("ws:");
    expect(url.pathname).toBe("/ws/terminal/");
    expect(url.searchParams.get("ticket")).toBe("a-single-use-ticket");
    expect(url.searchParams.get("cols")).toBe("120");
    expect(url.searchParams.get("rows")).toBe("40");
    expect(socket.binaryType).toBe("arraybuffer");
    expect(FakeTerminal.latest().focused).toBe(true);
    expect(screen.getByRole("status")).toHaveTextContent("connecting");
  });

  it("prints where the shell runs, and how the session can end, then the shell's output", async () => {
    const socket = await connect();
    act(() => socket.emitJson(sessionMessage));
    expect(screen.getByRole("status")).toHaveTextContent("connected");
    expect(screen.getByText("smarter_user@smarter-app-7d9f8c6b5-x2kqp")).toBeInTheDocument();
    expect(output()).toContain("bash --login on smarter-app-7d9f8c6b5-x2kqp, as smarter_user, pid 4242.");
    expect(output()).toContain("This session can end suddenly");
    expect(output()).toContain("after 30 minutes without input, and after 8 hours in any case.");
    expect(output()).toContain("a poor place for long-running processes");

    act(() => socket.emitOutput("smarter_user@smarter-app:~$ "));
    expect(output().endsWith("smarter_user@smarter-app:~$ ")).toBe(true);
  });

  it("sends what is typed, and the terminal's new size", async () => {
    const socket = await connect();
    act(() => socket.emitJson(sessionMessage));
    FakeTerminal.latest().type("ls -la\r");
    FakeTerminal.latest().resize(100, 30);
    expect(socket.messages()).toEqual([
      { type: "input", data: "ls -la\r" },
      { type: "resize", cols: 100, rows: 30 },
    ]);
  });

  it("says why the session ended, and starts a new one on Enter", async () => {
    const socket = await connect();
    act(() => socket.emitJson(sessionMessage));
    act(() => socket.emitJson({ type: "exit", reason: "idle", code: null }));
    expect(screen.getByRole("status")).toHaveTextContent("disconnected");
    expect(output()).toContain("The session ended after too long without input.");
    expect(output()).toContain("Press Enter to start a new session.");

    // typing does nothing until Enter.
    FakeTerminal.latest().type("x");
    expect(socket.messages()).toEqual([]);
    expect(FakeWebSocket.instances).toHaveLength(1);
    FakeTerminal.latest().type("\r");
    await waitFor(() => expect(FakeWebSocket.instances).toHaveLength(2));
    expect(screen.getByRole("status")).toHaveTextContent("connecting");
  });

  it("says when the connection drops", async () => {
    const socket = await connect();
    act(() => socket.emitJson(sessionMessage));
    act(() => socket.drop());
    expect(output()).toContain("The connection to the server closed, and the session ended.");
  });

  it("says when the WebSocket refuses the connection", async () => {
    const socket = await connect();
    act(() => socket.drop());
    expect(output()).toContain("The server refused the connection.");
  });

  it("says when the ticket api refuses", async () => {
    server.use(...ticketRefusedHandlers);
    render(<TerminalEmulator sessionContext={sessionContext} />);
    await waitFor(() => expect(output()).toContain("The server refused the connection."));
    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it("keeps the screen when the page is left, and redraws it, above a new session, when it is opened again", async () => {
    const socket = await connect();
    act(() => socket.emitJson(sessionMessage));
    act(() => socket.emitOutput("$ echo before\r\nbefore\r\n"));
    act(() => window.dispatchEvent(new Event("pagehide")));
    const kept = window.sessionStorage.getItem(SCREEN_KEY);
    expect(kept).toContain("before\r\n");
    // the plain terminal is kept: not a full screen program's alternate screen, nor its modes.
    expect(FakeSerializeAddon.options[0]).toEqual({ scrollback: 5000, excludeAltBuffer: true, excludeModes: true });

    rendered.unmount();
    written.length = 0;
    await connect();
    expect(output().startsWith(kept!)).toBe(true);
    expect(output()).toContain(
      "Restored from before this page was left. That shell has ended, and a new one starts below.",
    );
  });

  it("keeps the screen when it unmounts, e.g. on a visit to another page of the console", () => {
    const { unmount } = render(<TerminalEmulator sessionContext={sessionContext} />);
    FakeTerminal.latest().write("on screen");
    unmount();
    expect(window.sessionStorage.getItem(SCREEN_KEY)).toContain("on screen");
  });

  it("redraws nothing when nothing was kept", async () => {
    await connect();
    expect(output()).not.toContain("Restored from before");
  });

  it("closes the WebSocket, and disposes of the terminal, when it unmounts", async () => {
    render(<TerminalEmulator sessionContext={sessionContext} />).unmount();
    expect(FakeTerminal.latest().disposed).toBe(true);
    // the ticket arrives after the unmount: no WebSocket is opened.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(FakeWebSocket.instances).toHaveLength(0);
  });
});
