import { describe, expect, it } from "vitest";

import { DOCS, kindInfo } from "./kinds";

describe("kindInfo", () => {
  it("presents the plugins alike", () => {
    expect(kindInfo("SqlPlugin")).toEqual(kindInfo("ApiPlugin"));
    expect(kindInfo("SqlPlugin").docsUrl).toBe(`${DOCS}/smarter-resources/smarter-llmtool.html`);
  });

  it("links each kind to its documentation", () => {
    const kinds = [
      "LLMClient",
      "Provider",
      "MCPClient",
      "Extension",
      "Guardrail",
      "ApiConnection",
      "SqlConnection",
      "Secret",
      "SmarterAuthToken",
      "CustomDomain",
      "LLMHost",
      "LLMHostCompute",
      "Orchestrator",
      "Proxy",
      "Vectorstore",
      "Vectorsearch",
      "Budget",
    ];
    for (const kind of kinds) {
      const info = kindInfo(kind);
      expect(info.docsUrl.startsWith(DOCS)).toBe(true);
      expect(info.role).not.toBe("");
    }
    expect(kindInfo("Secret").tone).toBe("danger");
  });

  it("presents a kind that it doesn't know", () => {
    expect(kindInfo("Gadget")).toEqual({
      tone: "secondary",
      role: "A SAM resource",
      docsUrl: `${DOCS}/smarter-framework/smarter-manifests.html`,
    });
  });
});
