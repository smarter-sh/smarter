import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@test/server";

import { recordOnboarding } from "@/lib/api";
import { onboardingContext } from "@/mocks/context";

describe("recordOnboarding", () => {
  it("posts the hint and the outcome, with the CSRF token", async () => {
    document.cookie = "csrftoken=abc123; path=/";
    let request: { body: unknown; csrf: string | null } | null = null;
    server.use(
      http.post(onboardingContext.apiUrl, async ({ request: req }) => {
        request = { body: await req.json(), csrf: req.headers.get("X-CSRFToken") };
        return HttpResponse.json({ seen: ["sidebar_llmclients"] });
      }),
    );
    const response = await recordOnboarding(onboardingContext, "sidebar_llmclients", "clicked");
    expect(response.ok).toBe(true);
    expect(request).toEqual({ body: { hint: "sidebar_llmclients", outcome: "clicked" }, csrf: "abc123" });
  });

  it("throws when the api answers with an error", async () => {
    server.use(http.post(onboardingContext.apiUrl, () => HttpResponse.json({ error: "no" }, { status: 400 })));
    await expect(recordOnboarding(onboardingContext, "workbench_tour", "completed")).rejects.toThrow(
      "Request failed: 400",
    );
  });
});
