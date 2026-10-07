import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "@test/server";

import fetchDjangoUrl from "./django";
import type { SessionContext } from "./Types";

const sessionContext: SessionContext = {
  ApiUrl: "/api/listview/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/test",
  smarterClientVersion: "1.2.3",
  smarterRequestId: "request-1",
};

describe("fetchDjangoUrl", () => {
  it("POSTs json, with the CSRF token and Smarter's client headers", async () => {
    document.cookie = "csrftoken=token-123";
    let request: Request | undefined;
    server.use(
      http.post("/api/listview/owned/", ({ request: r }) => {
        request = r;
        return HttpResponse.json({ objects: [] });
      }),
    );

    const response = await fetchDjangoUrl(sessionContext, "/api/listview/owned/", JSON.stringify({ a: 1 }));

    expect(response.ok).toBe(true);
    expect(request!.headers.get("X-CSRFToken")).toBe("token-123");
    expect(request!.headers.get("Content-Type")).toBe("application/json");
    expect(request!.headers.get("X-Smarter-Client")).toBe("@smarter/test");
    expect(request!.headers.get("X-Smarter-ClientVersion")).toBe("1.2.3");
    expect(request!.headers.get("X-Smarter-RequestId")).toBe("request-1");
    expect(request!.headers.get("X-Smarter-Capabilities")).toBe("listview,cardview");
    expect(await request!.json()).toEqual({ a: 1 });
  });

  it("sends the session's capabilities", async () => {
    let capabilities: string | null = null;
    server.use(
      http.post("/api/x/", ({ request }) => {
        capabilities = request.headers.get("X-Smarter-Capabilities");
        return HttpResponse.json({});
      }),
    );
    await fetchDjangoUrl({ ...sessionContext, smarterCapabilities: ["prompt", "stream"] }, "/api/x/", "{}");
    expect(capabilities).toBe("prompt,stream");
  });
});
