import { afterEach, describe, expect, it, vi } from "vitest";

import { captureBaseUrl } from "./assets";
import { ASSETS_PLACEHOLDER, FONT_STYLE_ID, addCss, applyCss, embedCss, fontFaceRules, hoistFontFaces } from "./css";

const FONT = `@font-face{font-family:KaTeX_Main;src:url(${ASSETS_PLACEHOLDER}katex/fonts/KaTeX_Main-Regular.woff2) format("woff2")}`;

function shadowRoot(): ShadowRoot {
  return document.createElement("div").attachShadow({ mode: "open" });
}

describe("embed css", () => {
  afterEach(() => {
    document.getElementById(FONT_STYLE_ID)?.remove();
    captureBaseUrl(null);
  });

  it("collects the css of every import, with the urls of the embed's own files", () => {
    const script = document.createElement("script");
    script.src = "https://www.example.com/assets/embed.js";
    captureBaseUrl(script);
    addCss(".a{color:red}");
    addCss(FONT);
    const css = embedCss();
    expect(css).toContain(".a{color:red}");
    expect(css).toContain("url(https://www.example.com/assets/embed/katex/fonts/KaTeX_Main-Regular.woff2)");
    expect(css).not.toContain(ASSETS_PLACEHOLDER);
  });

  it("finds the @font-face rules, and adds them to the document's head once", () => {
    const css = `.a{color:red}${FONT}@font-face { font-family: Other; src: url(x.woff2) }`;
    expect(fontFaceRules(css)).toHaveLength(2);
    expect(fontFaceRules(".a{color:red}")).toEqual([]);
    hoistFontFaces(".a{color:red}");
    expect(document.getElementById(FONT_STYLE_ID)).toBeNull();
    hoistFontFaces(css);
    hoistFontFaces(css);
    const styles = document.querySelectorAll(`#${FONT_STYLE_ID}`);
    expect(styles).toHaveLength(1);
    expect(styles[0]).toHaveTextContent("font-family: Other");
    expect(styles[0]).not.toHaveTextContent(".a{");
  });

  it("applies the css to a shadow root as a style element, where constructable stylesheets aren't supported", () => {
    const root = shadowRoot();
    root.append(document.createElement("div"));
    applyCss(root, ".b{color:blue}");
    expect(root.firstChild).toBeInstanceOf(HTMLStyleElement);
    expect(root.firstChild?.textContent).toBe(".b{color:blue}");
  });

  it("adopts one shared constructable stylesheet, where they are supported", () => {
    class FakeSheet {
      css = "";
      replaceSync(css: string) {
        this.css = css;
      }
    }
    vi.stubGlobal("CSSStyleSheet", FakeSheet);
    const first = shadowRoot();
    const second = shadowRoot();
    for (const root of [first, second])
      Object.defineProperty(root, "adoptedStyleSheets", { value: [], writable: true });
    applyCss(first, ".c{}");
    applyCss(second, ".c{}");
    expect(first.adoptedStyleSheets).toHaveLength(1);
    expect(first.adoptedStyleSheets[0]).toBe(second.adoptedStyleSheets[0]);
    expect((first.adoptedStyleSheets[0] as unknown as FakeSheet).css).toBe(".c{}");
    expect(first.querySelector("style")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("falls back to a style element when the stylesheet can't be constructed", () => {
    vi.stubGlobal(
      "CSSStyleSheet",
      class {
        replaceSync() {
          throw new Error("not allowed");
        }
      },
    );
    // new css, so that the shared stylesheet of the previous test is constructed again.
    addCss("");
    const root = shadowRoot();
    Object.defineProperty(root, "adoptedStyleSheets", { value: [], writable: true });
    applyCss(root, ".d{}");
    expect(root.querySelector("style")?.textContent).toBe(".d{}");
    vi.unstubAllGlobals();
  });
});
