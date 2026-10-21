/**
 * The embed script's css, which it puts in each chat's shadow root, so that the website's own css can't change the
 * chat, and the chat's css can't change the website.
 *
 * The embed build turns every css import, e.g. chatscope's theme and SmarterChat's styles.css, into a call of
 * addCss() with the css as a string, rather than a stylesheet of the page. See vite.config.ts. KaTeX's fonts are
 * referred to as __SMARTER_CHAT_ASSETS__/katex/fonts/..., which embedCss() replaces with their url beside the script.
 *
 * Fonts are the exception to the shadow root: browsers don't apply @font-face rules in a shadow root to it, so they
 * are added to the page's head as well, once. Their names, e.g. KaTeX_Main, are the chat's own.
 */
import { assetUrl } from "./assets";

export const ASSETS_PLACEHOLDER = "__SMARTER_CHAT_ASSETS__/";
export const FONT_STYLE_ID = "smarter-chat-embed-fonts";

const registered: string[] = [];
let sheet: CSSStyleSheet | null = null;

/** Adds css to the embed's stylesheet. Called by the modules that the embed build generates for css imports. */
export function addCss(css: string): void {
  registered.push(css);
  sheet = null;
}

/** The embed's css, with the urls of its own files. */
export function embedCss(): string {
  return registered.join("\n").replaceAll(ASSETS_PLACEHOLDER, assetUrl(""));
}

/** The @font-face rules of a stylesheet. */
export function fontFaceRules(css: string): string[] {
  return css.match(/@font-face\s*\{[^}]*\}/g) ?? [];
}

/** Adds the @font-face rules of the css to the document's head, once. */
export function hoistFontFaces(css: string, doc: Document = document): void {
  if (doc.getElementById(FONT_STYLE_ID)) return;
  const rules = fontFaceRules(css);
  if (rules.length === 0) return;
  const style = doc.createElement("style");
  style.id = FONT_STYLE_ID;
  style.textContent = rules.join("\n");
  doc.head.append(style);
}

/** Whether the browser supports constructable stylesheets, which a page's Content Security Policy can't block. */
function canAdoptStyleSheets(root: ShadowRoot): boolean {
  return (
    "adoptedStyleSheets" in root && typeof CSSStyleSheet === "function" && "replaceSync" in CSSStyleSheet.prototype
  );
}

/**
 * Applies the css to a shadow root: as a constructable stylesheet, shared by every chat on the page, where the
 * browser supports them, or else as a style element.
 */
export function applyCss(root: ShadowRoot, css: string): void {
  if (canAdoptStyleSheets(root)) {
    try {
      if (!sheet) {
        sheet = new CSSStyleSheet();
        sheet.replaceSync(css);
      }
      root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
      return;
    } catch {
      sheet = null;
      // fall back to a style element.
    }
  }
  const style = root.ownerDocument.createElement("style");
  style.textContent = css;
  root.prepend(style);
}
