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

    expect(await load(sessionContext, true, "owned", onError)).toEqual([{ id: 1 }, { id: 2 }]);
    expect(new URL(url).searchParams.get("invalidate_cache")).toBe("true");
    expect(onError).toHaveBeenCalledWith(null);
    expect(getCookieForUrl("/api/listview/owned/")).toBe(2);
  });

  it("reports the api's error message", async () => {
    server.use(http.post("/api/listview/owned/", () => HttpResponse.json({ error: "Not allowed" }, { status: 403 })));
    const onError = vi.fn();
    expect(await load(sessionContext, false, "owned", onError)).toEqual([]);
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
