import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";

import { formatAllowedPaths, formatApiKey, formatAuth, proxyUrl, upstreamHost } from "./format";

describe("format", () => {
  it("makes the Proxy's url absolute, or empty without one", () => {
    expect(proxyUrl(makeObject(1))).toBe("http://localhost:9357/api/v1/proxy/example-1/");
    expect(proxyUrl(makeObject(1, { url: "" }))).toBe("");
  });

  it("finds the upstream host, else shows the upstream url as it is", () => {
    expect(upstreamHost(makeObject(1))).toBe("api.openai.com");
    expect(upstreamHost(makeObject(1, { upstreamUrl: "not a url" }))).toBe("not a url");
    expect(upstreamHost(makeObject(1, { upstreamUrl: "" }))).toBe("—");
  });

  it("formats the auth header, with its scheme if any", () => {
    expect(formatAuth(makeObject(1))).toBe("Authorization: Bearer");
    expect(formatAuth(makeObject(1, { authHeader: "x-api-key", authScheme: "" }))).toBe("x-api-key");
  });

  it("formats the API key: the Proxy's own, the provider's, or none", () => {
    expect(formatApiKey(makeObject(1, { apiKeySecret: 7, apiKeySecretName: "mine" } as never))).toBe("mine");
    expect(formatApiKey(makeObject(1))).toBe("openai_api_key (provider's)");
    expect(formatApiKey(makeObject(1, { apiKeySecretName: "" } as never))).toBe("None");
  });

  it("counts the allowed paths", () => {
    expect(formatAllowedPaths(makeObject(1))).toBe("All paths");
    expect(formatAllowedPaths(makeObject(1, { allowedPaths: undefined as never }))).toBe("All paths");
    expect(formatAllowedPaths(makeObject(1, { allowedPaths: ["/a"] }))).toBe("1 path");
    expect(formatAllowedPaths(makeObject(1, { allowedPaths: ["/a", "/b"] }))).toBe("2 paths");
  });
});
