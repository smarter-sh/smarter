import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@test/server";

import { useOnboarding } from "@/lib/useOnboarding";
import { onboardingContext } from "@/mocks/context";

describe("useOnboarding", () => {
  it("shows a hint that the user hasn't seen, and records it once", async () => {
    const posted: unknown[] = [];
    server.use(
      http.post(onboardingContext.apiUrl, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ seen: [] });
      }),
    );
    const { result } = renderHook(() => useOnboarding({ ...onboardingContext, seen: ["workbench_tour"] }));
    expect(result.current.enabled).toBe(true);
    expect(result.current.shouldShow("sidebar_llmclients")).toBe(true);
    expect(result.current.shouldShow("workbench_tour")).toBe(false);

    act(() => result.current.record("sidebar_llmclients", "clicked"));
    expect(result.current.shouldShow("sidebar_llmclients")).toBe(false);
    act(() => result.current.record("sidebar_llmclients", "dismissed"));
    act(() => result.current.record("workbench_tour", "completed"));
    await waitFor(() => expect(posted).toEqual([{ hint: "sidebar_llmclients", outcome: "clicked" }]));
  });

  it("shows nothing while hints are disabled, or on a page without onboarding state", () => {
    const { result: disabled } = renderHook(() => useOnboarding({ ...onboardingContext, enabled: false }));
    expect(disabled.current.shouldShow("sidebar_llmclients")).toBe(false);
    const { result: none } = renderHook(() => useOnboarding(null));
    expect(none.current.enabled).toBe(false);
    act(() => none.current.record("sidebar_llmclients", "clicked"));
  });

  it("reads the page's onboarding state by default", () => {
    const { result } = renderHook(() => useOnboarding());
    expect(result.current.enabled).toBe(false);
  });

  it("logs a failed request, and keeps the hint hidden on this page", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(onboardingContext.apiUrl, () => HttpResponse.json({}, { status: 500 })));
    const { result } = renderHook(() => useOnboarding(onboardingContext));
    act(() => result.current.record("llmclient_weather", "dismissed"));
    expect(result.current.shouldShow("llmclient_weather")).toBe(false);
    await waitFor(() => expect(error).toHaveBeenCalled());
  });
});
