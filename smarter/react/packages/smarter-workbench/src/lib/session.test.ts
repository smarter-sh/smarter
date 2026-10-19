import { describe, expect, it } from "vitest";

import { readConfig, ROOT_ID } from "@/lib/session";

function root(attributes: Record<string, string>): HTMLElement {
  const element = document.createElement("div");
  element.id = ROOT_ID;
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  return element;
}

const ATTRIBUTES = {
  "smarter-llmclient-api-url": "http://localhost:9357/workbench/llm-clients/rMTAwMDAwMQx/",
  "smarter-toggle-metadata": "True",
  "smarter-csrf-cookie-name": "csrftoken",
  "smarter-session-cookie-name": "session_key",
  "smarter-django-session-cookie-name": "sessionid",
  "smarter-cookie-domain": "",
  "react-debug-mode": "False",
  "smarter-request-id": "abc",
  "smarter-log-stream-url": "",
  "smarter-manifest-url": "/workbench/llm-clients/rMTAwMDAwMQx/manifest/editor/",
  "smarter-architecture-url": "/workbench/llm-clients/rMTAwMDAwMQx/architecture/",
  "smarter-deployment-url": "/workbench/llm-clients/rMTAwMDAwMQx/deployment/",
  "smarter-llmclient-list-url": "/workbench/",
  "smarter-apply-api-url": "/api/v1/cli/apply/",
  "smarter-validate-api-url": "/api/v1/cli/validate/",
  "smarter-delete-api-url": "/api/v1/cli/delete/__kind__/",
  "smarter-kind-placeholder": "__kind__",
};

describe("readConfig", () => {
  it("reads the workbench's configuration, as Django renders it", () => {
    const config = readConfig(root(ATTRIBUTES));
    expect(config.toggleMetadata).toBe(true);
    expect(config.debugMode).toBe(false);
    // an empty url is no tab.
    expect(config.logStreamUrl).toBeNull();
    expect(config.manifestUrl).toBe("/workbench/llm-clients/rMTAwMDAwMQx/manifest/editor/");
    expect(config.architectureUrl).toBe("/workbench/llm-clients/rMTAwMDAwMQx/architecture/");
    expect(config.cookieDomain).toBe(window.location.hostname);
    expect(config.session).toMatchObject({
      csrfCookieName: "csrftoken",
      djangoSessionCookieName: "sessionid",
      smarterRequestId: "abc",
      smarterClient: "@smarter/workbench",
    });
  });

  it("requires the chat's api, the cookies, and the cli api's urls", () => {
    for (const name of ["smarter-llmclient-api-url", "smarter-csrf-cookie-name", "smarter-apply-api-url"]) {
      const attributes: Record<string, string> = { ...ATTRIBUTES };
      delete attributes[name];
      expect(() => readConfig(root(attributes))).toThrow(name);
    }
  });
});
