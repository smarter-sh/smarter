import { afterEach, describe, expect, it } from "vitest";

import { publicPage } from "@/mocks/fixtures";
import { readContext, ROOT_ID } from "@/lib/session";

const DATA_ID = "smarter-llmclient-deployment-data";

/** The root element and the json_script, as Django renders them. */
function render(attributes: Record<string, string>, data: unknown = publicPage): HTMLElement {
  const script = document.createElement("script");
  script.id = DATA_ID;
  script.type = "application/json";
  script.textContent = JSON.stringify(data);
  document.body.appendChild(script);
  const element = document.createElement("div");
  element.id = ROOT_ID;
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  document.body.appendChild(element);
  return element;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("readContext", () => {
  it("reads the page at the deployed LLMClient's url, which has no session", () => {
    const context = readContext(render({ "smarter-deployment-data-id": DATA_ID }));
    expect(context.page).toEqual(publicPage);
    expect(context.session).toBeNull();
  });

  it("requires the data", () => {
    expect(() => readContext(render({}))).toThrow(/smarter-deployment-data-id/);
    document.body.innerHTML = "";
    expect(() => readContext(render({ "smarter-deployment-data-id": "missing" }))).toThrow(/was not found/);
    document.body.innerHTML = "";
    expect(() => readContext(render({ "smarter-deployment-data-id": DATA_ID }, null))).toThrow(/is empty/);
  });
});
