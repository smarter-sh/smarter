import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { sessionContext } from "@/mocks/fixtures";
import { server } from "@test/server";

import useDashboardApi from "@/hooks/useDashboardApi";

const URL = "/dashboard/api/x/";
const KEY = `smarter_dashboard_api:${URL}`;
const MINUTE = 60 * 1000;
const NOW = Date.UTC(2026, 9, 17, 12, 0, 0);
const STALE_CHECK_MS = 30 * 1000;

/** Serves answer 1, 2, 3, ... and counts the requests. */
function countingHandler() {
  const counter = { requests: 0 };
  server.use(
    http.post(URL, () => {
      counter.requests += 1;
      return HttpResponse.json({ answer: counter.requests });
    }),
  );
  return counter;
}

/** The id of the captured interval, which no real one has. */
const CAPTURED_ID = -1;

/**
 * Captures the interval that the hook sets, so that a test can run it. Testing Library's waitFor()
 * polls with short intervals of its own, which still run.
 */
function captureInterval() {
  const captured: { tick?: () => void; ms?: number } = {};
  const setInterval = window.setInterval.bind(window);
  const clearInterval = window.clearInterval.bind(window);
  vi.spyOn(window, "setInterval").mockImplementation(((handler: () => void, ms: number) => {
    if (ms < STALE_CHECK_MS) return setInterval(handler, ms);
    captured.tick = handler;
    captured.ms = ms;
    return CAPTURED_ID;
  }) as typeof window.setInterval);
  vi.spyOn(window, "clearInterval").mockImplementation((id?: Parameters<typeof window.clearInterval>[0]) => {
    if (id !== CAPTURED_ID) clearInterval(id);
  });
  return captured;
}

function setVisibility(state: DocumentVisibilityState) {
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => state });
}

afterEach(() => {
  setVisibility("visible");
});

describe("useDashboardApi", () => {
  it("returns the api's data", async () => {
    server.use(http.post(URL, () => HttpResponse.json({ answer: 42 })));
    const { result } = renderHook(() => useDashboardApi<{ answer: number }>(sessionContext, URL));
    expect(result.current).toMatchObject({ data: null, error: null, refreshing: false });
    await waitFor(() => expect(result.current.data).toEqual({ answer: 42 }));
    expect(window.localStorage.getItem(KEY)).toBeNull();
  });

  it("returns the request's error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(URL, () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useDashboardApi(sessionContext, URL));
    await waitFor(() => expect(result.current.error).toBe("Request failed: 500"));
  });

  it("requests nothing without a url", () => {
    // an unhandled request would fail the test.
    const { result } = renderHook(() => useDashboardApi(sessionContext, ""));
    expect(result.current.data).toBeNull();
  });

  it("keeps the response, and a later page load shows it at once, without a request", async () => {
    const counter = countingHandler();
    const { result: firstLoad, unmount } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: 5 * MINUTE }),
    );
    await waitFor(() => expect(firstLoad.current.data).toEqual({ answer: 1 }));
    unmount();

    const { result: secondLoad } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: 5 * MINUTE }),
    );
    expect(secondLoad.current.data).toEqual({ answer: 1 });
    expect(counter.requests).toBe(1);
  });

  it("requests again when the kept response is too old", async () => {
    const counter = countingHandler();
    window.localStorage.setItem(KEY, JSON.stringify({ savedAt: Date.now() - 6 * MINUTE, data: { answer: 0 } }));
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: 5 * MINUTE }),
    );
    expect(result.current.data).toBeNull();
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));
    expect(counter.requests).toBe(1);
  });

  it("ignores a kept response that it can't read", async () => {
    countingHandler();
    window.localStorage.setItem(KEY, "not json");
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: 5 * MINUTE }),
    );
    expect(result.current.data).toBeNull();
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));
  });

  it("still works when storage is blocked", async () => {
    countingHandler();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: 5 * MINUTE }),
    );
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));
  });

  it("requests again once the response is refreshMs old, while the page is visible", async () => {
    const counter = countingHandler();
    const interval = captureInterval();
    const now = vi.spyOn(Date, "now").mockReturnValue(NOW);
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { refreshMs: 5 * MINUTE }),
    );
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));
    expect(interval.ms).toBe(STALE_CHECK_MS);

    // not stale yet: no request.
    now.mockReturnValue(NOW + 4 * MINUTE);
    act(() => interval.tick?.());
    expect(counter.requests).toBe(1);

    // stale, but hidden: no request.
    now.mockReturnValue(NOW + 5 * MINUTE);
    setVisibility("hidden");
    act(() => interval.tick?.());
    expect(counter.requests).toBe(1);

    // visible again: the stale response is refreshed at once.
    setVisibility("visible");
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await waitFor(() => expect(result.current.data).toEqual({ answer: 2 }));
  });

  it("counts the age of a kept response from when it was first received", async () => {
    const counter = countingHandler();
    const interval = captureInterval();
    const now = vi.spyOn(Date, "now").mockReturnValue(NOW);
    window.localStorage.setItem(KEY, JSON.stringify({ savedAt: NOW - 4 * MINUTE, data: { answer: 0 } }));
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: 5 * MINUTE, refreshMs: 5 * MINUTE }),
    );
    expect(result.current.data).toEqual({ answer: 0 });

    now.mockReturnValue(NOW + MINUTE);
    act(() => interval.tick?.());
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));
    expect(counter.requests).toBe(1);
    expect(JSON.parse(window.localStorage.getItem(KEY) as string)).toEqual({
      savedAt: NOW + MINUTE,
      data: { answer: 1 },
    });
  });

  it("retries a failed request at the next check", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const interval = captureInterval();
    let fail = true;
    server.use(
      http.post(URL, () => (fail ? new HttpResponse(null, { status: 503 }) : HttpResponse.json({ answer: 1 }))),
    );
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { refreshMs: 5 * MINUTE }),
    );
    await waitFor(() => expect(result.current.error).toBe("Request failed: 503"));

    fail = false;
    act(() => interval.tick?.());
    await waitFor(() => expect(result.current).toMatchObject({ data: { answer: 1 }, error: null }));
  });

  it("doesn't request again while a request is in flight", async () => {
    const interval = captureInterval();
    let requests = 0;
    let release: () => void = () => {};
    server.use(
      http.post(URL, async () => {
        requests += 1;
        await new Promise<void>((resolve) => {
          release = resolve;
        });
        return HttpResponse.json({ answer: requests });
      }),
    );
    const { result } = renderHook(() =>
      useDashboardApi<{ answer: number }>(sessionContext, URL, { refreshMs: MINUTE }),
    );
    await waitFor(() => expect(requests).toBe(1));
    act(() => interval.tick?.());
    expect(requests).toBe(1);
    release();
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));
  });

  it("requests again now on refresh(), with its body, and says it's refreshing until it settles", async () => {
    const bodies: unknown[] = [];
    let release: () => void = () => {};
    server.use(
      http.post(URL, async ({ request }) => {
        bodies.push(await request.json());
        if (bodies.length > 1) {
          await new Promise<void>((resolve) => {
            release = resolve;
          });
        }
        return HttpResponse.json({ answer: bodies.length });
      }),
    );
    const { result } = renderHook(() => useDashboardApi<{ answer: number }>(sessionContext, URL, { maxAgeMs: MINUTE }));
    await waitFor(() => expect(result.current.data).toEqual({ answer: 1 }));

    act(() => result.current.refresh({ refresh: true }));
    expect(result.current.refreshing).toBe(true);
    await waitFor(() => expect(bodies).toEqual([{}, { refresh: true }]));
    release();
    await waitFor(() => expect(result.current).toMatchObject({ data: { answer: 2 }, refreshing: false }));
    expect(JSON.parse(window.localStorage.getItem(KEY) as string).data).toEqual({ answer: 2 });
  });

  it("refresh() does nothing without a url", () => {
    const { result } = renderHook(() => useDashboardApi(sessionContext, ""));
    act(() => result.current.refresh());
    expect(result.current.refreshing).toBe(false);
  });

  it("stops polling when it unmounts", async () => {
    countingHandler();
    captureInterval();
    const removeListener = vi.spyOn(document, "removeEventListener");
    const { result, unmount } = renderHook(() => useDashboardApi(sessionContext, URL, { refreshMs: 5 * MINUTE }));
    await waitFor(() => expect(result.current.data).not.toBeNull());
    unmount();
    expect(window.clearInterval).toHaveBeenCalledWith(CAPTURED_ID);
    expect(removeListener).toHaveBeenCalledWith("visibilitychange", expect.any(Function));
  });
});
