import { describe, expect, it } from "vitest";

import getPromptTemplate, { promptTemplates } from "./templates";

describe("getPromptTemplate", () => {
  it("fills the template with the provider's model", () => {
    expect(JSON.parse(getPromptTemplate(1, "gpt-4o-mini"))).toEqual({
      model: "gpt-4o-mini",
      ...promptTemplates[0].body,
    });
  });

  it("falls back to the first template", () => {
    expect(getPromptTemplate(999, "m")).toBe(getPromptTemplate(promptTemplates[0].id, "m"));
  });

  it("requires a template and a model", () => {
    expect(() => getPromptTemplate(0, "m")).toThrow("templateId is required");
    expect(() => getPromptTemplate(1, "")).toThrow("defaultModel is required");
  });
});
