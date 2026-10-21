/**
 * The embed script's options: the attributes of a <smarter-chat> element, the data- attributes of the script tag,
 * or the properties of window.SmarterChatConfig, which all have the same names, in kebab-case for attributes and in
 * camelCase for window.SmarterChatConfig. Only "chatbot" is required.
 *
 * Every value comes from a web page, which may have been written by hand, so each one is checked: a size or a color
 * that isn't a plain css value, or a mode or a position that doesn't exist, is replaced by its default.
 */
import { safeCssValue } from "@/lib/styles";

export type EmbedMode = "launcher" | "inline";
export type EmbedPosition = "bottom-right" | "bottom-left";

export interface EmbedOptions {
  /** The url of the deployed LLMClient, e.g. https://support.3141-5926-5359.api.example.com/ */
  chatbot: string;
  /** A Smarter api key, for LLMClients that require one. It is public, as is everything in a web page. */
  apiKey: string | null;
  /** "launcher": a button in a corner of the page that opens the chat. "inline": the chat, in the page. */
  mode: EmbedMode;
  /** The launcher's corner. */
  position: EmbedPosition;
  /** Whether the launcher starts open. */
  open: boolean;
  /** The launcher's accessible name, and the chat panel's. Null for the default, "Chat", in the chat's language. */
  label: string | null;
  /** The launcher button's background color. */
  color: string;
  /** The width of the inline chat, or of the launcher's panel. */
  width: string;
  /** The height of the inline chat, or of the launcher's panel. */
  height: string;
  /** The launcher's z-index. */
  zIndex: number;
  /** The cookie in which the chat saves its session's key. */
  sessionCookieName: string;
  /** The path of the chat's cookies. "/" keeps one chat session across the website. */
  cookiePath: string;
  /** Display a running prompt's progress. */
  streamProgress: boolean;
  /** Log to the browser console. */
  debug: boolean;
  /** The language of the chat's own text, e.g. "fr". Null for the page's, or else the browser's. */
  language: string | null;
}

/** The result of reading the options: the options, or why they can't be used. */
export type EmbedOptionsResult = { options: EmbedOptions; error: null } | { options: null; error: string };

/** The attributes that a <smarter-chat> element reads, in kebab-case. */
export const OPTION_ATTRIBUTES = [
  "chatbot",
  "api-key",
  "mode",
  "position",
  "open",
  "label",
  "color",
  "width",
  "height",
  "z-index",
  "session-cookie-name",
  "cookie-path",
  "stream-progress",
  "debug",
  "language",
] as const;

export const DEFAULT_COLOR = "#ff5733";
// the topmost layer that pages use, less a little, so that a page's own topmost elements, e.g. a cookie banner,
// can still cover the launcher.
export const DEFAULT_Z_INDEX = 2147483000;
const DEFAULT_SIZES: Record<EmbedMode, { width: string; height: string }> = {
  launcher: { width: "400px", height: "600px" },
  inline: { width: "100%", height: "600px" },
};

/** A boolean attribute: present and empty, or "true", is true. "false" is false. Missing is the default. */
export function booleanOption(value: string | null | undefined, defaultValue: boolean): boolean {
  if (value === null || value === undefined) return defaultValue;
  const normalized = value.trim().toLowerCase();
  if (normalized === "" || normalized === "true") return true;
  if (normalized === "false") return false;
  return defaultValue;
}

/** The url, if it is an http(s) url, normalized to end with a slash, else null. */
export function chatbotUrl(value: string | null | undefined): string | null {
  if (!value?.trim()) return null;
  try {
    const url = new URL(value.trim());
    if (url.protocol !== "https:" && url.protocol !== "http:") return null;
    if (!url.pathname.endsWith("/")) url.pathname = `${url.pathname}/`;
    return url.toString();
  } catch {
    return null;
  }
}

/**
 * The default session cookie of a chatbot: one per chatbot host, so that two chatbots on one website keep separate
 * chat sessions, e.g. smarter_chat_support_3141_5926_5359_api_example_com.
 */
export function defaultSessionCookieName(chatbot: string): string {
  return `smarter_chat_${new URL(chatbot).host.replace(/[^A-Za-z0-9]/g, "_")}`;
}

/**
 * The options of a <smarter-chat> element.
 *
 * @param get Returns the value of an attribute, by its kebab-case name, or null if it is missing.
 * @param defaultMode The mode, if the attributes don't say: "inline" for an element in the page, and "launcher"
 *   for the element that the script tag adds.
 */
export function parseOptions(
  get: (name: (typeof OPTION_ATTRIBUTES)[number]) => string | null,
  defaultMode: EmbedMode = "inline",
): EmbedOptionsResult {
  const chatbot = chatbotUrl(get("chatbot"));
  if (!chatbot) {
    return {
      options: null,
      error: `"chatbot" must be the http(s) url of a deployed LLMClient, not ${JSON.stringify(get("chatbot"))}.`,
    };
  }
  const modeValue = get("mode")?.trim().toLowerCase();
  const mode: EmbedMode = modeValue === "launcher" || modeValue === "inline" ? modeValue : defaultMode;
  const position: EmbedPosition =
    get("position")?.trim().toLowerCase() === "bottom-left" ? "bottom-left" : "bottom-right";
  const zIndex = Number.parseInt(get("z-index") ?? "", 10);
  const cookiePath = get("cookie-path")?.trim();
  const sessionCookieName = get("session-cookie-name")?.trim();
  return {
    error: null,
    options: {
      chatbot,
      apiKey: get("api-key")?.trim() || null,
      mode,
      position,
      open: booleanOption(get("open"), false),
      label: get("label")?.trim() || null,
      color: safeCssValue(get("color")) ?? DEFAULT_COLOR,
      width: safeCssValue(get("width")) ?? DEFAULT_SIZES[mode].width,
      height: safeCssValue(get("height")) ?? DEFAULT_SIZES[mode].height,
      zIndex: Number.isFinite(zIndex) ? zIndex : DEFAULT_Z_INDEX,
      sessionCookieName:
        sessionCookieName && /^[A-Za-z0-9_.-]+$/.test(sessionCookieName)
          ? sessionCookieName
          : defaultSessionCookieName(chatbot),
      cookiePath: cookiePath?.startsWith("/") ? cookiePath : "/",
      streamProgress: booleanOption(get("stream-progress"), true),
      debug: booleanOption(get("debug"), false),
      // a language tag, e.g. "es-MX". Anything else is ignored, and SmarterChat falls back to English.
      language: get("language")?.trim() || null,
    },
  };
}

/** A camelCase name in kebab-case, e.g. apiKey to api-key. */
export function kebabCase(name: string): string {
  return name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
}

/**
 * The attributes of a configuration object, e.g. window.SmarterChatConfig's, or a script tag's dataset: kebab-case
 * names, and string values. Values that are null, undefined, objects or functions are left out.
 */
export function configAttributes(config: Record<string, unknown>): Record<string, string> {
  const attributes: Record<string, string> = {};
  for (const [name, value] of Object.entries(config)) {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      attributes[kebabCase(name)] = String(value);
    }
  }
  return attributes;
}
