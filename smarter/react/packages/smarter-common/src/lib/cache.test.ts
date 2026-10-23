import { afterEach, describe, expect, it, vi } from "vitest";

import { MAX_ENTRIES, makeCacheKey, pruneCache, readCache, sessionScope, writeCache } from "./cache";
import type { Pagination } from "./Types";

const PAGINATION: Pagination = {
  page: 2,
  pageSize: 10,
  numPages: 3,
  count: 25,
  search: "",
  ordering: "-name",
  sortFields: ["name"],
};

describe("cache", () => {
  afterEach(() => {
    vi.useRealTimers();
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
  });

  it("makes a key per api url, tab, page, ordering, filter and session", () => {
    const base = makeCacheKey("/a/", "owned");
    expect(base).not.toBe(makeCacheKey("/a/", "shared"));
    expect(base).toContain("/a/owned");
    expect(base).toBe(makeCacheKey("/a/", "owned", { page: 1, ordering: "", filter: "" }));
    expect(base).not.toBe(makeCacheKey("/a/", "owned", { page: 2 }));
    expect(base).not.toBe(makeCacheKey("/a/", "owned", { ordering: "-name" }));
    expect(base).not.toBe(makeCacheKey("/a/", "owned", { filter: "pending" }));
    expect(base).not.toBe(makeCacheKey("/a/", "owned", {}, "abc"));
  });

  it("scopes keys by a hash of the session's csrf cookie, without holding it", () => {
    const context = { csrfCookieName: "csrftoken", cookieDomain: "localhost" };
    expect(sessionScope(context)).toBe("");
    document.cookie = "csrftoken=first-session-token; path=/";
    const first = sessionScope(context);
    expect(first).toMatch(/^[0-9a-f]+$/);
    expect(first).not.toContain("first-session-token");
    document.cookie = "csrftoken=next-session-token; path=/";
    expect(sessionScope(context)).not.toBe(first);
  });

  it("reads what it wrote, with its pagination, from localStorage", () => {
    writeCache("key", [{ id: 1 }], PAGINATION);
    expect(readCache("key")).toEqual({ objects: [{ id: 1 }], pagination: PAGINATION });
    expect(localStorage.getItem("key")).not.toBeNull();
    writeCache("no-pagination", [{ id: 2 }]);
    expect(readCache("no-pagination")).toEqual({ objects: [{ id: 2 }], pagination: null });
  });

  it("returns null for a missing or corrupt entry", () => {
    expect(readCache("missing")).toBeNull();
    localStorage.setItem("corrupt", "{not json");
    expect(readCache("corrupt")).toBeNull();
    localStorage.setItem("wrong-shape", JSON.stringify({ objects: "no" }));
    expect(readCache("wrong-shape")).toBeNull();
  });

  it("drops an entry after a week", () => {
    vi.useFakeTimers({ now: new Date("2026-06-01T00:00:00Z") });
    writeCache("key", [{ id: 1 }]);
    vi.setSystemTime(new Date("2026-06-09T00:00:00Z"));
    expect(readCache("key")).toBeNull();
    expect(localStorage.getItem("key")).toBeNull();
  });

  it("keeps only the most recent entries, and none expired", () => {
    vi.useFakeTimers({ now: new Date("2026-06-01T00:00:00Z") });
    const expired = makeCacheKey("/a/", "owned", { page: 999 });
    writeCache(expired, [{ id: 0 }]);
    vi.setSystemTime(new Date("2026-06-09T00:00:00Z"));
    for (let page = 1; page <= MAX_ENTRIES + 5; page++) {
      vi.setSystemTime(new Date(Date.now() + 1000));
      writeCache(makeCacheKey("/a/", "owned", { page }), [{ id: page }]);
    }
    pruneCache();
    expect(localStorage.getItem(expired)).toBeNull();
    expect(readCache(makeCacheKey("/a/", "owned", { page: 1 }))).toBeNull();
    expect(readCache(makeCacheKey("/a/", "owned", { page: MAX_ENTRIES + 5 }))).not.toBeNull();
    localStorage.setItem("someone-elses-key", "kept");
    pruneCache();
    expect(localStorage.getItem("someone-elses-key")).toBe("kept");
  });

  it("treats unavailable storage as a cache miss", () => {
    const getItem = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    expect(() => writeCache("key", [{ id: 1 }])).not.toThrow();
    expect(readCache("key")).toBeNull();
    getItem.mockRestore();
    setItem.mockRestore();
  });
});
