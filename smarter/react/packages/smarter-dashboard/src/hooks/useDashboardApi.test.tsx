import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { sessionContext } from "@/mocks/fixtures";
import { server } from "@test/server";

import useDashboardApi from "@/hooks/useDashboardApi";

describe("useDashboardApi", () => {
  it("returns the api's data", async () => {
    server.use(http.post("/dashboard/api/x/", () => HttpResponse.json({ answer: 42 })));
    const { result } = renderHook(() => useDashboardApi<{ answer: number }>(sessionContext, "/dashboard/api/x/"));
    expect(result.current).toEqual({ data: null, error: null });
    await waitFor(() => expect(result.current.data).toEqual({ answer: 42 }));
  });

  it("returns the request's error", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post("/dashboard/api/x/", () => new HttpResponse(null, { status: 500 })));
    const { result } = renderHook(() => useDashboardApi(sessionContext, "/dashboard/api/x/"));
    await waitFor(() => expect(result.current.error).toBe("Request failed: 500"));
  });

  it("requests nothing without a url", () => {
    // an unhandled request would fail the test.
    const { result } = renderHook(() => useDashboardApi(sessionContext, ""));
    expect(result.current.data).toBeNull();
  });
});
