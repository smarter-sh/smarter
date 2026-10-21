import { afterEach, describe, expect, it } from "vitest";

import { CDN_BASE_URL, assetUrl, captureBaseUrl, scriptBaseUrl } from "./assets";

function script(src: string): HTMLScriptElement {
  const element = document.createElement("script");
  element.src = src;
  return element;
}

describe("assets", () => {
  afterEach(() => {
    captureBaseUrl(null);
  });

  it("finds the embed's files beside the script, wherever it is served from", () => {
    expect(scriptBaseUrl(script("https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0.9.0/dist/embed.js"))).toBe(
      "https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0.9.0/dist/",
    );
    captureBaseUrl(script("https://www.example.com/wp-content/plugins/smarter-chat/assets/embed.js?ver=0.9.0"));
    expect(assetUrl("mermaid/mermaid.js")).toBe(
      "https://www.example.com/wp-content/plugins/smarter-chat/assets/embed/mermaid/mermaid.js",
    );
  });

  it("uses jsDelivr's copy of this version when the script has no url", () => {
    expect(CDN_BASE_URL).toMatch(/^https:\/\/cdn\.jsdelivr\.net\/npm\/@smarter\.sh\/ui-chat@\d+\.\d+\.\d+.*\/dist\/$/);
    expect(scriptBaseUrl(null)).toBe(CDN_BASE_URL);
    expect(scriptBaseUrl(document.createElement("script"))).toBe(CDN_BASE_URL);
    expect(scriptBaseUrl(document.createElement("div"))).toBe(CDN_BASE_URL);
    expect(captureBaseUrl(undefined)).toBe(CDN_BASE_URL);
    expect(assetUrl("katex/fonts/KaTeX_Main-Regular.woff2")).toBe(
      `${CDN_BASE_URL}embed/katex/fonts/KaTeX_Main-Regular.woff2`,
    );
  });
});
