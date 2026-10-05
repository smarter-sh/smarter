import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource, installFakes } from "@/mocks/fakes";
import { STREAM_URL, bulkLogs, liveLog } from "@/mocks/fixtures";

import { useLogStream } from "./logStream";

describe("useLogStream", () => {
  beforeEach(() => {
    installFakes();
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("connects, and receives the recent logs, then each new one", () => {
    const { result } = renderHook(() => useLogStream(STREAM_URL));
    const stream = FakeEventSource.latest();
    expect(stream.url).toBe(STREAM_URL);
    expect(result.current).toMatchObject({ connected: false, isInitializing: true, logs: [] });

    act(() => stream.open());
    expect(result.current.connected).toBe(true);

    act(() => stream.emit(bulkLogs, "bulk"));
    expect(result.current.logs).toEqual(bulkLogs);
    expect(result.current.isInitializing).toBe(false);

    act(() => stream.emit(liveLog));
    expect(result.current.logs).toEqual([...bulkLogs, liveLog]);
  });

  it("accepts a message that is plain text", () => {
    const { result } = renderHook(() => useLogStream(STREAM_URL));
    act(() => FakeEventSource.latest().emit("plain text line"));
    expect(result.current.logs).toEqual([{ message: "plain text line" }]);
  });

  it("reports a disconnection", () => {
    const { result } = renderHook(() => useLogStream(STREAM_URL));
    act(() => FakeEventSource.latest().open());
    act(() => FakeEventSource.latest().fail());
    expect(result.current).toMatchObject({
      connected: false,
      isInitializing: false,
      error: "Log stream disconnected. Reconnecting...",
    });
  });

  it("closes the stream when it is unmounted", () => {
    const { unmount } = renderHook(() => useLogStream(STREAM_URL));
    unmount();
    expect(FakeEventSource.latest().closed).toBe(true);
  });
});
