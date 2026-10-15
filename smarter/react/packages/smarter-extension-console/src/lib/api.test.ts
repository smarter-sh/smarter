import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import * as api from "@/lib/api";
import { API_URL, action, listContext, listResponse } from "@/mocks/fixtures";
import { server } from "@test/server";

describe("the api client", () => {
  it("posts JSON with Django's headers, and returns the response", async () => {
    let headers: Headers | undefined;
    let body: unknown;
    server.use(
      http.post(`${API_URL}install/`, async ({ request }) => {
        headers = request.headers;
        body = await request.json();
        return HttpResponse.json(action("Installed."));
      }),
    );
    document.cookie = "csrftoken=token";
    const result = await api.install(listContext, "weather", "0.2.0");
    expect(result.message).toBe("Installed.");
    expect(body).toEqual({ slug: "weather", version: "0.2.0" });
    expect(headers?.get("X-CSRFToken")).toBe("token");
    expect(headers?.get("X-Smarter-ClientType")).toBe("react");
  });

  it("throws the api's error message, or the status", async () => {
    server.use(
      http.post(`${API_URL}list/`, () =>
        HttpResponse.json({ error: "Only superusers may manage extensions." }, { status: 403 }),
      ),
      http.post(`${API_URL}registry/`, () => new HttpResponse("<html>", { status: 502, statusText: "Bad Gateway" })),
    );
    await expect(api.listExtensions(listContext)).rejects.toMatchObject({
      message: "Only superusers may manage extensions.",
      status: 403,
    });
    await expect(api.getRegistry(listContext)).rejects.toThrow("The request failed: 502 Bad Gateway");
  });

  it("builds each extension's urls", async () => {
    const paths: string[] = [];
    server.use(
      http.post(`${API_URL}*`, ({ request }) => {
        paths.push(new URL(request.url).pathname.replace(API_URL, ""));
        return HttpResponse.json(action("Done."));
      }),
    );
    await api.getExtension(listContext, "date-calculator");
    await api.enable(listContext, "weather");
    await api.disable(listContext, "weather");
    await api.update(listContext, "weather");
    await api.rollback(listContext, "weather", 3);
    await api.configure(listContext, "weather", { values: {} });
    await api.setAvailability(listContext, "weather", { allAccounts: true });
    await api.uninstall(listContext, "weather");
    await api.checkUpdates(listContext);
    await api.getAccounts(listContext);
    expect(paths).toEqual([
      "extensions/date-calculator/",
      "extensions/weather/enable/",
      "extensions/weather/disable/",
      "extensions/weather/update/",
      "extensions/weather/rollback/",
      "extensions/weather/configure/",
      "extensions/weather/availability/",
      "extensions/weather/uninstall/",
      "check-updates/",
      "accounts/",
    ]);
  });

  it("uploads an archive as multipart, with the CSRF token", async () => {
    let contentType: string | null = null;
    let csrf: string | null = null;
    server.use(
      http.post(`${API_URL}upload/`, ({ request }) => {
        contentType = request.headers.get("Content-Type");
        csrf = request.headers.get("X-CSRFToken");
        return HttpResponse.json(action("Installed."));
      }),
    );
    document.cookie = "csrftoken=token";
    const result = await api.uploadArchive(listContext, new File(["zip"], "weather-0.1.0.zip"));
    expect(result.message).toBe("Installed.");
    expect(contentType).toMatch(/^multipart\/form-data/);
    expect(csrf).toBe("token");
    expect(listResponse.objects.length).toBeGreaterThan(0);
  });
});
