import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import { getCookieForUrl } from "../components/TabbedListView/cookie";
import { load } from "./load";
import type { SessionContext } from "./Types";

const sessionContext = {
  ApiUrl: "/api/listview/",
  csrfCookieName: "csrftoken",
  cookieDomain: "localhost",
} as SessionContext;

describe("load", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  it("loads a tab's objects, and remembers how many there were", async () => {
    let url = "";
    server.use(
      http.post("/api/listview/owned/", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ objects: [{ id: 1 }, { id: 2 }] });
      }),
    );
    const onError = vi.fn();

    expect(await load(sessionContext, true, "owned", onError)).toEqual({
      objects: [{ id: 1 }, { id: 2 }],
      pagination: null,
    });
    const params = new URL(url).searchParams;
    expect(params.get("invalidate_cache")).toBe("true");
    expect([params.get("page"), params.get("page_size"), params.get("search"), params.get("ordering")]).toEqual([
      null,
      null,
      null,
      null,
    ]);
    expect(onError).toHaveBeenCalledWith(null);
    expect(getCookieForUrl("/api/listview/owned/")).toBe(2);
  });

  it("requests a sorted page of the objects that match a search, and returns its pagination", async () => {
    let url = "";
    const pagination = {
      page: 2,
      pageSize: 10,
      numPages: 3,
      count: 21,
      search: "bot",
      ordering: "-name",
      sortFields: ["name"],
    };
    server.use(
      http.post("/api/listview/shared/", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ objects: [{ id: 11 }], pagination });
      }),
    );
    const result = await load(sessionContext, false, "shared", vi.fn(), {
      page: 2,
      pageSize: 10,
      search: "  bot ",
      ordering: "-name",
    });
    expect(result).toEqual({ objects: [{ id: 11 }], pagination });
    const params = new URL(url).searchParams;
    expect([params.get("page"), params.get("page_size"), params.get("search"), params.get("ordering")]).toEqual([
      "2",
      "10",
      "bot",
      "-name",
    ]);
  });

  it("does not request an empty search, or the default order", async () => {
    let url = "";
    server.use(
      http.post("/api/listview/owned/", ({ request }) => {
        url = request.url;
        return HttpResponse.json({ objects: [] });
      }),
    );
    await load(sessionContext, false, "owned", vi.fn(), { search: "   ", ordering: "" });
    expect(new URL(url).searchParams.has("search")).toBe(false);
    expect(new URL(url).searchParams.has("ordering")).toBe(false);
  });

  it("reports the api's error message", async () => {
    server.use(http.post("/api/listview/owned/", () => HttpResponse.json({ error: "Not allowed" }, { status: 403 })));
    const onError = vi.fn();
    expect(await load(sessionContext, false, "owned", onError)).toEqual({ objects: [], pagination: null });
    expect(onError).toHaveBeenLastCalledWith("Not allowed");
  });

  it("reports the status of an error without a message", async () => {
    server.use(http.post("/api/listview/owned/", () => new HttpResponse("oops", { status: 502 })));
    const onError = vi.fn();
    await load(sessionContext, false, "owned", onError);
    expect(onError).toHaveBeenLastCalledWith("Failed to load objects (502)");
  });

  it("rejects a response without an objects array", async () => {
    server.use(http.post("/api/listview/owned/", () => HttpResponse.json({ items: [] })));
    const onError = vi.fn();
    await load(sessionContext, false, "owned", onError);
    expect(onError).toHaveBeenLastCalledWith("Invalid response payload: expected objects array.");
  });
});
