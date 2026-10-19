import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource, installFakes } from "@/mocks/fakes";
import { LOG_STREAM_URL, bulkLogs, liveLog } from "@/mocks/fixtures";

import {
  MAX_LOG_EVENTS,
  SANDBOX_LOG_LEVEL,
  logStreamUrlForChat,
  logStreamUrlForLevel,
  useLogStream,
} from "./logStream";

describe("logStreamUrlForLevel", () => {
  it("adds the log level to the url, and leaves the url alone without one", () => {
    expect(logStreamUrlForLevel(LOG_STREAM_URL, SANDBOX_LOG_LEVEL)).toBe(`${LOG_STREAM_URL}?level=DEBUG`);
    expect(logStreamUrlForLevel(`${LOG_STREAM_URL}?level=INFO&x=1`, "DEBUG")).toBe(`${LOG_STREAM_URL}?level=DEBUG&x=1`);
    expect(logStreamUrlForLevel("/dashboard/logs/api/stream/", "DEBUG")).toBe(
      `${window.location.origin}/dashboard/logs/api/stream/?level=DEBUG`,
    );
    expect(logStreamUrlForLevel(LOG_STREAM_URL, null)).toBe(LOG_STREAM_URL);
    expect(logStreamUrlForLevel(null, "DEBUG")).toBeNull();
  });
});

describe("logStreamUrlForChat", () => {
  const sessionKey = "a".repeat(64);

  it("narrows the stream to the chat session, at the log level", () => {
    expect(logStreamUrlForChat(LOG_STREAM_URL, sessionKey)).toBe(`${LOG_STREAM_URL}?session_key=${sessionKey}`);
    expect(logStreamUrlForChat(LOG_STREAM_URL, sessionKey, SANDBOX_LOG_LEVEL)).toBe(
      `${LOG_STREAM_URL}?level=DEBUG&session_key=${sessionKey}`,
    );
  });

  it("has no stream without a url or a session key", () => {
    expect(logStreamUrlForChat(null, sessionKey)).toBeNull();
    expect(logStreamUrlForChat(LOG_STREAM_URL, null, SANDBOX_LOG_LEVEL)).toBeNull();
    expect(logStreamUrlForChat(LOG_STREAM_URL, "")).toBeNull();
  });
});

describe("useLogStream", () => {
  beforeEach(() => installFakes());
  afterEach(() => vi.unstubAllGlobals());

  it("does not connect without a url", () => {
    renderHook(() => useLogStream(null));
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("connects with the browser's cookies, and receives the recent logs, then each new one", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    const stream = FakeEventSource.latest();
    expect(stream.url).toBe(LOG_STREAM_URL);
    expect(stream.init).toEqual({ withCredentials: true });
    expect(result.current).toMatchObject({ connected: false, logs: [] });

    act(() => stream.open());
    expect(result.current.connected).toBe(true);

    act(() => stream.emit(bulkLogs, "bulk"));
    expect(result.current.logs).toEqual(bulkLogs);

    act(() => stream.emit(liveLog));
    expect(result.current.logs).toEqual([...bulkLogs, liveLog]);
  });

  it("starts a new url, e.g. a new chat session's, with no records", () => {
    const { result, rerender } = renderHook(({ url }) => useLogStream(url), { initialProps: { url: LOG_STREAM_URL } });
    act(() => FakeEventSource.latest().open());
    act(() => FakeEventSource.latest().emit(bulkLogs, "bulk"));
    expect(result.current.logs).toEqual(bulkLogs);

    const otherUrl = `${LOG_STREAM_URL}?session_key=${"b".repeat(64)}`;
    rerender({ url: otherUrl });
    expect(result.current).toMatchObject({ connected: false, logs: [] });
    expect(FakeEventSource.latest().url).toBe(otherUrl);
  });

  it("accepts records that are plain text, and ignores a malformed history", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    act(() => FakeEventSource.latest().emit("{not json", "bulk"));
    act(() => FakeEventSource.latest().emit("plain text line"));
    act(() => FakeEventSource.latest().emit({ no: "message" }));
    expect(result.current.logs).toEqual([{ message: "plain text line" }, { message: '{"no":"message"}' }]);
  });

  it("keeps only the most recent records", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    const records = Array.from({ length: MAX_LOG_EVENTS + 1 }, (_, index) => ({ message: `log ${index}` }));
    act(() => FakeEventSource.latest().emit(records, "bulk"));
    expect(result.current.logs).toHaveLength(MAX_LOG_EVENTS);
    act(() => FakeEventSource.latest().emit({ message: "newest" }));
    expect(result.current.logs).toHaveLength(MAX_LOG_EVENTS);
    expect(result.current.logs.at(-1)).toEqual({ message: "newest" });
    expect(result.current.logs[0]).toEqual({ message: "log 2" });
  });

  it("clears its records, and doesn't display the older ones again", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    const stream = FakeEventSource.latest();
    act(() => stream.emit(bulkLogs, "bulk"));
    act(() => result.current.clear());
    expect(result.current.logs).toEqual([]);

    // e.g. a reconnection, which replays the history, and records that were in transit.
    act(() => stream.emit(bulkLogs, "bulk"));
    act(() => stream.emit(liveLog));
    expect(result.current.logs).toEqual([]);

    const newer = { message: "newer", timestamp: String(Date.now() / 1000 + 60) };
    const untimed = { message: "untimed" };
    act(() => stream.emit(newer));
    act(() => stream.emit(untimed));
    expect(result.current.logs).toEqual([newer, untimed]);
  });

  it("reports a disconnection", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    act(() => FakeEventSource.latest().open());
    act(() => FakeEventSource.latest().fail());
    expect(result.current).toMatchObject({ connected: false, error: "The log stream disconnected. Reconnecting..." });
  });

  it("closes the stream when it is unmounted", () => {
    const { unmount } = renderHook(() => useLogStream(LOG_STREAM_URL));
    unmount();
    expect(FakeEventSource.latest().closed).toBe(true);
  });
});
