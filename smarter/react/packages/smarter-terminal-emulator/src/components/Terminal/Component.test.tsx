import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource, installFakes, written } from "@/mocks/fakes";
import { STREAM_URL, bulkLogs, liveLog } from "@/mocks/fixtures";

import TerminalEmulator from "./Component";

vi.mock("@xterm/xterm", async () => ({ Terminal: (await import("@/mocks/fakes")).FakeTerminal }));
vi.mock("@xterm/addon-fit", async () => ({ FitAddon: (await import("@/mocks/fakes")).FakeFitAddon }));
vi.mock("@xterm/xterm/css/xterm.css", () => ({}));

describe("TerminalEmulator", () => {
  beforeEach(() => {
    installFakes();
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("shows whether the stream is connected", () => {
    render(<TerminalEmulator apiUrl={STREAM_URL} />);
    expect(screen.getByText("disconnected")).toBeInTheDocument();
    act(() => FakeEventSource.latest().open());
    expect(screen.getByText("connected")).toBeInTheDocument();
  });

  it("writes the recent logs, without the stream's own status lines, then each new one", () => {
    render(<TerminalEmulator apiUrl={STREAM_URL} />);
    const stream = FakeEventSource.latest();

    act(() => stream.emit(bulkLogs, "bulk"));
    const output = written.join("");
    expect(output).toContain(bulkLogs[1].message);
    expect(output).toContain(bulkLogs[2].message);
    expect(output).not.toContain("[stream] connected");

    act(() => stream.emit(liveLog));
    expect(written.join("")).toContain(liveLog.message);
  });

  it("writes a disconnection to the terminal", () => {
    render(<TerminalEmulator apiUrl={STREAM_URL} />);
    act(() => FakeEventSource.latest().fail());
    expect(written.join("")).toContain("Log stream disconnected. Reconnecting...");
  });

  it("shows a loading indicator only when the logs are slow to arrive", () => {
    vi.useFakeTimers();
    try {
      render(<TerminalEmulator apiUrl={STREAM_URL} />);
      expect(screen.queryByLabelText("Loading logs")).not.toBeInTheDocument();
      act(() => vi.advanceTimersByTime(300));
      expect(screen.getByLabelText("Loading logs")).toBeInTheDocument();
      act(() => FakeEventSource.latest().emit(bulkLogs, "bulk"));
      expect(screen.queryByLabelText("Loading logs")).not.toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});
