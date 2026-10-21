import { describe, expect, it } from "vitest";

import {
  DEFAULT_COLOR,
  DEFAULT_Z_INDEX,
  booleanOption,
  chatbotUrl,
  configAttributes,
  defaultSessionCookieName,
  kebabCase,
  parseOptions,
} from "./options";

const CHATBOT = "https://support.3141-5926-5359.api.example.com/";

function parse(attributes: Record<string, string>, defaultMode?: "launcher" | "inline") {
  return parseOptions((name) => attributes[name] ?? null, defaultMode);
}

describe("parseOptions", () => {
  it("needs only a chatbot, and has a default for everything else", () => {
    expect(parse({ chatbot: CHATBOT })).toEqual({
      error: null,
      options: {
        chatbot: CHATBOT,
        apiKey: null,
        mode: "inline",
        position: "bottom-right",
        open: false,
        label: null,
        color: DEFAULT_COLOR,
        width: "100%",
        height: "600px",
        zIndex: DEFAULT_Z_INDEX,
        sessionCookieName: "smarter_chat_support_3141_5926_5359_api_example_com",
        cookiePath: "/",
        streamProgress: true,
        debug: false,
        language: null,
      },
    });
  });

  it("reads every attribute", () => {
    const { options } = parse({
      chatbot: "https://chat.example.com/sales",
      "api-key": " abc ",
      mode: "Launcher",
      position: "bottom-left",
      open: "",
      label: "Ask us",
      color: "rgb(0, 128, 0)",
      width: "360px",
      height: "70vh",
      "z-index": "10",
      "session-cookie-name": "sales_session",
      "cookie-path": "/shop/",
      "stream-progress": "false",
      debug: "true",
      language: " es-MX ",
    });
    expect(options).toEqual({
      chatbot: "https://chat.example.com/sales/",
      apiKey: "abc",
      mode: "launcher",
      position: "bottom-left",
      open: true,
      label: "Ask us",
      color: "rgb(0, 128, 0)",
      width: "360px",
      height: "70vh",
      zIndex: 10,
      sessionCookieName: "sales_session",
      cookiePath: "/shop/",
      streamProgress: false,
      debug: true,
      language: "es-MX",
    });
  });

  it("uses the default mode, and the launcher's panel size, when the attributes don't say", () => {
    const { options } = parse({ chatbot: CHATBOT }, "launcher");
    expect(options).toMatchObject({ mode: "launcher", width: "400px", height: "600px" });
  });

  it("replaces values that aren't valid with their defaults", () => {
    const { options } = parse({
      chatbot: CHATBOT,
      mode: "popup",
      position: "top-left",
      color: "red; background: url(https://evil.example.com/)",
      height: "expression(alert(1))",
      "z-index": "high",
      "session-cookie-name": "a cookie; path=/",
      "cookie-path": "shop",
      debug: "maybe",
    });
    expect(options).toMatchObject({
      mode: "inline",
      position: "bottom-right",
      color: DEFAULT_COLOR,
      height: "600px",
      zIndex: DEFAULT_Z_INDEX,
      sessionCookieName: "smarter_chat_support_3141_5926_5359_api_example_com",
      cookiePath: "/",
      debug: false,
    });
  });

  it("is an error without a chatbot, or with one that isn't an http(s) url", () => {
    expect(parse({})).toEqual({ options: null, error: expect.stringContaining("null") });
    expect(parse({ chatbot: "javascript:alert(1)" }).error).toContain("javascript:alert(1)");
    expect(parse({ chatbot: "not a url" }).options).toBeNull();
  });
});

describe("helpers", () => {
  it("booleanOption reads present, true and false, and keeps the default otherwise", () => {
    expect(booleanOption("", false)).toBe(true);
    expect(booleanOption(" TRUE ", false)).toBe(true);
    expect(booleanOption("false", true)).toBe(false);
    expect(booleanOption(null, true)).toBe(true);
    expect(booleanOption(undefined, false)).toBe(false);
    expect(booleanOption("yes", false)).toBe(false);
  });

  it("chatbotUrl accepts http(s) urls, and adds the trailing slash", () => {
    expect(chatbotUrl("http://localhost:9357/api/v1/llm-clients/3")).toBe(
      "http://localhost:9357/api/v1/llm-clients/3/",
    );
    expect(chatbotUrl(CHATBOT)).toBe(CHATBOT);
    expect(chatbotUrl("  ")).toBeNull();
    expect(chatbotUrl("ftp://example.com/")).toBeNull();
  });

  it("defaultSessionCookieName is one cookie per chatbot host", () => {
    expect(defaultSessionCookieName("http://localhost:9357/")).toBe("smarter_chat_localhost_9357");
  });

  it("configAttributes converts a configuration object to attributes", () => {
    expect(kebabCase("sessionCookieName")).toBe("session-cookie-name");
    expect(
      configAttributes({
        chatbot: CHATBOT,
        apiKey: "k",
        open: true,
        zIndex: 5,
        target: "#chat",
        nested: {},
        gone: null,
      }),
    ).toEqual({ chatbot: CHATBOT, "api-key": "k", open: "true", "z-index": "5", target: "#chat" });
  });
});
