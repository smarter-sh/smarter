import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LOG_WRAP_STORAGE_KEY, useLogWrap } from "./logWrap";

describe("useLogWrap", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("scrolls long lines until the user wraps them, and remembers the choice", () => {
    const { result } = renderHook(() => useLogWrap());
    expect(result.current[0]).toBe(false);

    act(() => result.current[1](true));
    expect(result.current[0]).toBe(true);
    expect(window.localStorage.getItem(LOG_WRAP_STORAGE_KEY)).toBe("true");

    act(() => result.current[1]((previous) => !previous));
    expect(result.current[0]).toBe(false);
    expect(window.localStorage.getItem(LOG_WRAP_STORAGE_KEY)).toBe("false");
  });

  it("wraps as the user last chose", () => {
    window.localStorage.setItem(LOG_WRAP_STORAGE_KEY, "true");
    const { result } = renderHook(() => useLogWrap());
    expect(result.current[0]).toBe(true);
  });

  it("works without storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    const { result } = renderHook(() => useLogWrap());
    expect(result.current[0]).toBe(false);
    act(() => result.current[1](true));
    expect(result.current[0]).toBe(true);
  });
});
