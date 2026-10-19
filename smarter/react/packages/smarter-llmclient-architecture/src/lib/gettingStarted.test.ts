import { describe, expect, it } from "vitest";

import {
  EXTENSION_SNIPPET,
  GUARDRAIL_SNIPPET,
  hasGuardrail,
  hasTools,
  MCPCLIENT_SNIPPET,
  PLUGIN_SNIPPET,
  STYLES_SNIPPET,
} from "@/lib/gettingStarted";
import { leafTree, lockedTree, stackademyTree } from "@/mocks/fixtures";

describe("hasGuardrail", () => {
  it("is whether the LLMClient itself has a Guardrail, even one that the user can't read", () => {
    expect(hasGuardrail(stackademyTree)).toBe(true);
    expect(hasGuardrail(lockedTree)).toBe(true);
    expect(hasGuardrail(leafTree)).toBe(false);
  });
});

describe("hasTools", () => {
  it("is whether the LLMClient itself has a plugin, an Extension or an MCPClient", () => {
    expect(hasTools(stackademyTree)).toBe(true);
    expect(hasTools(lockedTree)).toBe(false);
    expect(hasTools(leafTree)).toBe(false);
    for (const kind of ["SqlPlugin", "StaticPlugin", "Extension", "MCPClient"]) {
      expect(hasTools({ ...leafTree, children: [{ ...leafTree, kind }] })).toBe(true);
    }
  });

  it("doesn't count a tool that only another resource uses", () => {
    const provider = { ...leafTree, kind: "Provider", children: [{ ...leafTree, kind: "SqlPlugin" }] };
    expect(hasTools({ ...leafTree, children: [provider] })).toBe(false);
  });
});

describe("the manifest excerpts", () => {
  it("are indented to go beneath their context", () => {
    for (const snippet of [GUARDRAIL_SNIPPET, PLUGIN_SNIPPET, EXTENSION_SNIPPET, MCPCLIENT_SNIPPET]) {
      expect(snippet.context).toBe("spec:");
      expect(snippet.code.startsWith("  ")).toBe(true);
      expect(snippet.code.startsWith("   ")).toBe(false);
    }
    expect(STYLES_SNIPPET.code.startsWith("    styles:\n")).toBe(true);
    expect(STYLES_SNIPPET.context).toContain("    prompt:");
  });

  it("use spaces, not tabs, which YAML forbids", () => {
    for (const snippet of [GUARDRAIL_SNIPPET, PLUGIN_SNIPPET, EXTENSION_SNIPPET, MCPCLIENT_SNIPPET, STYLES_SNIPPET]) {
      expect(snippet.code).not.toContain("\t");
    }
  });
});
