import { afterEach, describe, expect, it, vi } from "vitest";

import { makeCacheKey, readCache, writeCache } from "./cache";

describe("cache", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("makes a key per api url and tab", () => {
    expect(makeCacheKey("/a/", "owned")).not.toBe(makeCacheKey("/a/", "shared"));
    expect(makeCacheKey("/a/", "owned")).toContain("/a/owned");
  });

  it("reads what it wrote", () => {
    writeCache("key", [{ id: 1 }]);
    expect(readCache("key")).toEqual([{ id: 1 }]);
  });

  it("returns null for a missing or corrupt entry", () => {
    expect(readCache("missing")).toBeNull();
    sessionStorage.setItem("corrupt", "{not json");
    expect(readCache("corrupt")).toBeNull();
    sessionStorage.setItem("wrong-shape", JSON.stringify({ objects: "no" }));
    expect(readCache("wrong-shape")).toBeNull();
  });

  it("drops an entry after a week", () => {
    vi.useFakeTimers({ now: new Date("2026-06-01T00:00:00Z") });
    writeCache("key", [{ id: 1 }]);
    vi.setSystemTime(new Date("2026-06-09T00:00:00Z"));
    expect(readCache("key")).toBeNull();
    expect(sessionStorage.getItem("key")).toBeNull();
  });
});
