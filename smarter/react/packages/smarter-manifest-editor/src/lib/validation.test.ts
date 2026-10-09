import { describe, expect, it, vi } from "vitest";

import { SECRET_YAML, VALIDATE_API_URL, sessionContext } from "@/mocks/fixtures";
import { invalidHandler } from "@/mocks/handlers";
import { server } from "@test/server";
import { http, HttpResponse } from "msw";

import { keyOffsets, locOffset, samErrors, syntaxErrors, yamlKeys } from "./validation";

describe("syntaxErrors", () => {
  it("finds none in valid YAML", () => {
    expect(syntaxErrors(SECRET_YAML)).toEqual([]);
  });

  it("locates a syntax error", () => {
    const yaml = "kind: Secret\nmetadata:\n  name: [unclosed\n";
    const [error] = syntaxErrors(yaml);
    expect(error.source).toBe("yaml");
    expect(error.offset).toBeGreaterThan(yaml.indexOf("metadata"));
  });
});

describe("keyOffsets and locOffset", () => {
  it("locate each key, nested ones and list items included", () => {
    const yaml = "kind: Secret\nspec:\n  config:\n    value: x\nitems:\n  - a\n  - b\n";
    const offsets = keyOffsets(yaml);
    expect(offsets.get("kind")).toBe(0);
    expect(offsets.get("spec.config.value")).toBe(yaml.indexOf("value"));
    expect(offsets.get("items.1")).toBe(yaml.indexOf("b"));
  });

  it("fall back to the nearest key that exists", () => {
    const offsets = keyOffsets("spec:\n  config: {}\n");
    expect(locOffset(offsets, ["spec", "config", "missing"])).toBe(offsets.get("spec.config"));
    expect(locOffset(offsets, ["nothing"])).toBe(0);
  });
});

describe("yamlKeys", () => {
  it("records where each scalar value ends, and the first of duplicate keys", () => {
    const yaml = "kind: Secret\nkind: Plugin\n";
    expect(yamlKeys(yaml).get("kind")).toEqual({ start: 0, end: "kind: Secret".length });
  });

  it("follows aliases", () => {
    const keys = yamlKeys("a: &x 1\nb: *x\nc: 3\n");
    expect(keys.get("b")).toEqual({ start: "a: &x 1\n".length });
    expect(keys.get("c")?.end).toBe("a: &x 1\nb: *x\nc: 3".length);
  });

  it("locates the items of a sequence of mappings", () => {
    const yaml = "items:\n  - name: a\n  - name: b\n";
    const keys = yamlKeys(yaml);
    expect(keys.get("items.1")?.start).toBe(yaml.lastIndexOf("name"));
    expect(keys.get("items.1.name")?.end).toBe(yaml.length - 1);
  });

  it("doesn't fail on a complex key, which manifests don't have", () => {
    expect(() => yamlKeys("? - a\n: b\nc: d\n")).not.toThrow();
  });

  it("finds nothing in YAML that doesn't parse", () => {
    expect(yamlKeys("kind: [unclosed").size).toBe(0);
  });
});

describe("samErrors", () => {
  it("locates the SAM model's errors in the YAML", async () => {
    server.use(invalidHandler);
    const errors = await samErrors(sessionContext, VALIDATE_API_URL, SECRET_YAML, {});
    expect(errors).toEqual([
      {
        source: "sam",
        message: "value must be at least 32 characters",
        loc: ["spec", "config", "value"],
        offset: SECRET_YAML.indexOf("value:"),
      },
    ]);
  });

  it("reports no errors when the api cannot validate", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(http.post(VALIDATE_API_URL, () => new HttpResponse(null, { status: 500 })));
    expect(await samErrors(sessionContext, VALIDATE_API_URL, SECRET_YAML, {})).toEqual([]);
  });

  it("reports no errors when the api's response has no data", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    server.use(http.post(VALIDATE_API_URL, () => HttpResponse.json({})));
    expect(await samErrors(sessionContext, VALIDATE_API_URL, SECRET_YAML, {})).toEqual([]);
  });

  it("reports no errors when the api lists none", async () => {
    server.use(http.post(VALIDATE_API_URL, () => HttpResponse.json({ data: { valid: true } })));
    expect(await samErrors(sessionContext, VALIDATE_API_URL, SECRET_YAML, {})).toEqual([]);
  });

  it("locates an error without a path at the start, with a default message", async () => {
    server.use(http.post(VALIDATE_API_URL, () => HttpResponse.json({ data: { valid: false, errors: [{}] } })));
    expect(await samErrors(sessionContext, VALIDATE_API_URL, SECRET_YAML, {})).toEqual([
      { source: "sam", message: "Invalid value", offset: 0, loc: [] },
    ]);
  });
});
