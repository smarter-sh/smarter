import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FakeEventSource, installFakes } from "@/mocks/fakes";
import { LOG_STREAM_URL, bulkLogs, liveLog } from "@/mocks/fixtures";

import { MAX_LOG_EVENTS, logStreamUrlForRequest, newRequestId, useLogStream } from "./logStream";

describe("logStreamUrlForRequest", () => {
  it("narrows the stream to a request's records, at every level", () => {
    expect(logStreamUrlForRequest(LOG_STREAM_URL, "abc")).toBe(`${LOG_STREAM_URL}?request_id=abc&level=DEBUG`);
    expect(logStreamUrlForRequest("/dashboard/logs/api/stream/", "abc", "INFO")).toBe(
      `${window.location.origin}/dashboard/logs/api/stream/?request_id=abc&level=INFO`,
    );
  });

  it("has no stream without a url or a request id", () => {
    expect(logStreamUrlForRequest(null, "abc")).toBeNull();
    expect(logStreamUrlForRequest(LOG_STREAM_URL, null)).toBeNull();
  });
});

describe("newRequestId", () => {
  it("makes a new id of 32 hexadecimal digits each time", () => {
    const id = newRequestId();
    expect(id).toMatch(/^[0-9a-f]{32}$/);
    expect(newRequestId()).not.toBe(id);
  });

  it("makes one without crypto.randomUUID", () => {
    vi.stubGlobal("crypto", {});
    expect(newRequestId()).toMatch(/^[0-9a-f]{32}$/);
    vi.unstubAllGlobals();
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

    act(() => stream.open());
    expect(result.current.connected).toBe(true);
    act(() => stream.emit(bulkLogs, "bulk"));
    act(() => stream.emit(liveLog));
    expect(result.current.logs).toEqual([...bulkLogs, liveLog]);
  });

  it("accepts records that are plain text, and ignores a malformed history", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    act(() => FakeEventSource.latest().emit("{not json", "bulk"));
    act(() => FakeEventSource.latest().emit({ not: "a list" }, "bulk"));
    act(() => FakeEventSource.latest().emit("plain text line"));
    expect(result.current.logs).toEqual([{ message: "plain text line" }]);
  });

  it("keeps only the most recent records", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    const records = Array.from({ length: MAX_LOG_EVENTS + 1 }, (_, index) => ({ message: `log ${index}` }));
    act(() => FakeEventSource.latest().emit(records, "bulk"));
    expect(result.current.logs).toHaveLength(MAX_LOG_EVENTS);
    expect(result.current.logs[0]).toEqual({ message: "log 1" });
  });

  it("starts a new url with no records, and closes the previous stream", () => {
    const { result, rerender } = renderHook(({ url }) => useLogStream(url), { initialProps: { url: LOG_STREAM_URL } });
    const first = FakeEventSource.latest();
    act(() => first.open());
    act(() => first.emit(bulkLogs, "bulk"));

    rerender({ url: `${LOG_STREAM_URL}?request_id=next` });
    expect(first.closed).toBe(true);
    expect(FakeEventSource.latest().url).toBe(`${LOG_STREAM_URL}?request_id=next`);
    expect(result.current).toMatchObject({ logs: [], connected: false, error: null });
  });

  it("reports a disconnection, until it reconnects", () => {
    const { result } = renderHook(() => useLogStream(LOG_STREAM_URL));
    act(() => FakeEventSource.latest().fail());
    expect(result.current).toMatchObject({
      connected: false,
      error: "The log stream disconnected. Reconnecting...",
    });
    act(() => FakeEventSource.latest().open());
    expect(result.current).toMatchObject({ connected: true, error: null });
  });
});
