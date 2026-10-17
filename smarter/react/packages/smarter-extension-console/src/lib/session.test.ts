import { describe, expect, it } from "vitest";

import { DETAIL_ROOT_ID, LIST_ROOT_ID, readContext } from "@/lib/session";

function root(id: string, attributes: Record<string, string>): HTMLElement {
  const element = document.createElement("div");
  element.id = id;
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  return element;
}

const ATTRIBUTES = {
  "smarter-extension-api-url": "/extensions/react-integration/api/",
  "smarter-extension-list-url": "/extensions/",
  "django-csrf-cookie-name": "csrftoken",
  "django-session-cookie-name": "sessionid",
  "smarter-request-id": "abc",
  "react-debug-mode": "True",
};

describe("readContext", () => {
  it("reads the list page's context, without a slug", () => {
    const context = readContext(root(LIST_ROOT_ID, ATTRIBUTES));
    expect(context.apiUrl).toBe("/extensions/react-integration/api/");
    expect(context.listUrl).toBe("/extensions/");
    expect(context.slug).toBeUndefined();
    expect(context.session.debugMode).toBe(true);
    expect(context.session.cookieDomain).toBe(window.location.hostname);
    expect(context.canEdit).toBe(false);
  });

  it("reads whether the user may manage extensions", () => {
    expect(readContext(root(LIST_ROOT_ID, { ...ATTRIBUTES, "smarter-extension-can-edit": "true" })).canEdit).toBe(true);
    expect(readContext(root(LIST_ROOT_ID, { ...ATTRIBUTES, "smarter-extension-can-edit": "false" })).canEdit).toBe(
      false,
    );
  });

  it("reads an extension page's slug", () => {
    expect(readContext(root(DETAIL_ROOT_ID, { ...ATTRIBUTES, "smarter-extension-slug": "weather" })).slug).toBe(
      "weather",
    );
  });

  it("requires the api's url, and a detail page's slug", () => {
    const { "smarter-extension-api-url": _api, ...withoutApi } = ATTRIBUTES;
    expect(() => readContext(root(LIST_ROOT_ID, withoutApi))).toThrow(/smarter-extension-api-url/);
    expect(() => readContext(root(DETAIL_ROOT_ID, ATTRIBUTES))).toThrow(/smarter-extension-slug/);
  });
});
