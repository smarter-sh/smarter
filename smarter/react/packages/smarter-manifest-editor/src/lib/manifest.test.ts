import { describe, expect, it } from "vitest";

import { SECRET_IN_USE_YAML, SECRET_YAML } from "@/mocks/fixtures";

import { cloneManifest, manifestDependencies, manifestToApply, parseManifest } from "./manifest";

describe("parseManifest", () => {
  it("parses a SAM manifest", () => {
    expect(parseManifest(SECRET_YAML)).toMatchObject({ kind: "Secret", metadata: { name: "example_secret" } });
  });

  it.each([
    ["is not an object", "just a string", "not a YAML object"],
    ["has no Smarter apiVersion", "apiVersion: v1\nkind: Secret\nmetadata:\n  name: x\n", "apiVersion"],
    ["has no kind", "apiVersion: smarter.sh/v1\nmetadata:\n  name: x\n", "kind is missing"],
    ["has no name", "apiVersion: smarter.sh/v1\nkind: Secret\nmetadata: {}\n", "metadata.name is missing"],
  ])("rejects a manifest that %s", (_, yaml, message) => {
    expect(() => parseManifest(yaml)).toThrow(message);
  });
});

describe("manifestToApply and cloneManifest", () => {
  it("drop the read-only status, and clone with a new name", () => {
    const manifest = parseManifest(SECRET_YAML);
    expect(manifestToApply(manifest)).not.toHaveProperty("status");
    const clone = cloneManifest(manifest, "copy");
    expect(clone.metadata).toMatchObject({ name: "copy", description: "An example secret." });
    expect(clone).not.toHaveProperty("status");
    expect(manifest.metadata.name).toBe("example_secret");
  });
});

describe("manifestDependencies", () => {
  it("lists the resources that depend on the manifest's", () => {
    expect(manifestDependencies(parseManifest(SECRET_IN_USE_YAML))).toEqual([
      { kind: "LLMClient", name: "example_llmclient" },
    ]);
    expect(manifestDependencies(parseManifest(SECRET_YAML))).toEqual([]);
    expect(manifestDependencies(null)).toEqual([]);
  });
});
