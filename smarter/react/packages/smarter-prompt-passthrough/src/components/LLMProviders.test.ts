import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { PROVIDER_API_URL, providers } from "@/mocks/fixtures";
import { server } from "@test/server";

import LLMProviders from "./LLMProviders";

describe("LLMProviders", () => {
  it.each([
    ["{ providers: [...] }", { providers }],
    ["a list", providers],
  ])("accepts %s, and drops entries that are not providers", async (_, body) => {
    const payload = Array.isArray(body) ? [...body, { id: "x" }] : { providers: [...body.providers, { id: "x" }] };
    server.use(http.post(PROVIDER_API_URL, () => HttpResponse.json(payload)));
    expect((await LLMProviders(PROVIDER_API_URL)).map((p) => p.name)).toEqual(["openai", "anthropic"]);
  });

  it("accepts a single provider", async () => {
    server.use(http.post(PROVIDER_API_URL, () => HttpResponse.json(providers[0])));
    expect(await LLMProviders(PROVIDER_API_URL)).toEqual([providers[0]]);
  });

  it("throws when the api fails", async () => {
    server.use(http.post(PROVIDER_API_URL, () => new HttpResponse(null, { status: 500 })));
    await expect(LLMProviders(PROVIDER_API_URL)).rejects.toThrow("Failed to fetch providers: 500");
  });
});
