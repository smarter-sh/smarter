/** The console's calls to the backend. */
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "@test/server";

import { ApiError, getJson, postJson } from "@/lib/api";
import { userSession } from "@/mocks/fixtures";

describe("getJson()", () => {
  it("returns the JSON body, and sends the Smarter headers", async () => {
    let client = "";
    server.use(
      http.get("/api/web/example/", ({ request }) => {
        client = request.headers.get("X-Smarter-Client") ?? "";
        return HttpResponse.json({ ok: true });
      }),
    );
    expect(await getJson("/api/web/example/")).toEqual({ ok: true });
    expect(client).toBe("@smarter/console");
  });

  it("throws an ApiError with the status and body of a failed call", async () => {
    server.use(http.get("/api/web/example/", () => HttpResponse.text("Not found", { status: 404 })));
    const error = await getJson("/api/web/example/").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).body).toBe("Not found");
  });
});

describe("ApiError", () => {
  it("keeps a failed POST's JSON body", async () => {
    server.use(http.post("/api/web/example/", () => HttpResponse.json({ email: ["Required."] }, { status: 400 })));
    const error = await postJson("/api/web/example/", {}, userSession.cookies).catch((e: unknown) => e);
    expect((error as ApiError).body).toEqual({ email: ["Required."] });
    expect((error as ApiError).message).toBe("/api/web/example/ answered 400");
  });
});

describe("postJson()", () => {
  it("sends JSON with the CSRF token from its cookie", async () => {
    document.cookie = "csrftoken=token-123; path=/";
    let csrfToken = "";
    let body: unknown = null;
    server.use(
      http.post("/api/web/example/", async ({ request }) => {
        csrfToken = request.headers.get("X-CSRFToken") ?? "";
        body = await request.json();
        return HttpResponse.json({ saved: true });
      }),
    );
    const response = await postJson("/api/web/example/", { name: "x" }, userSession.cookies);
    expect(response).toEqual({ saved: true });
    expect(csrfToken).toBe("token-123");
    expect(body).toEqual({ name: "x" });
  });

  it("uses the page's host when the session names no cookie domain", async () => {
    document.cookie = "csrftoken=token-456; path=/";
    let csrfToken = "";
    server.use(
      http.post("/api/web/example/", ({ request }) => {
        csrfToken = request.headers.get("X-CSRFToken") ?? "";
        return HttpResponse.json({});
      }),
    );
    await postJson("/api/web/example/", {}, { ...userSession.cookies, cookieDomain: "" });
    expect(csrfToken).toBe("token-456");
  });
});
