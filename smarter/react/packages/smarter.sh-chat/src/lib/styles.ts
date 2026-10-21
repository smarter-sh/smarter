/**
 * The LLMClient's styles: its manifest's spec.config.styles, which the config api returns, with
 * snake_case keys, as llmclient.styles.
 *
 * chatscope's theme (@chatscope/chat-ui-kit-styles) is compiled from scss variables, so its colors
 * can't be changed at run time. Instead, the styles become css custom properties (variables) on the
 * chat's root element, e.g. --smarter-chat-header-bg, which styles.css applies to chatscope's
 * components, with chatscope's (or Smarter's) own value as the fallback. A setting that is left out
 * changes nothing.
 *
 * The backend validates every value. They are checked again here, because a page may embed a chat
 * from any Smarter platform: a value that isn't a plain css value is ignored.
 */
import { useEffect, type CSSProperties } from "react";

import type { Contract } from "@/types";

export type ChatStyles = Contract.PromptChatApiStyles;
export type ChatStyleSection = Contract.PromptChatApiStyleSection;

/** A plain css value: no declarations, blocks, escapes or functions, other than colors' functions. */
const SAFE_CSS_VALUE = /^[^;{}<>\\@!]{1,200}$/;
const COLOR_FUNCTION = /\b(rgba?|hsla?)\([0-9.%\s,/+-]*\)/gi;
const SAFE_IMAGE_URL = /^https:\/\/[^\s"'()<>\\]{1,2048}$/;
const SAFE_GOOGLE_FONT = /^[A-Za-z0-9 ]{1,64}$/;

/** The id of the stylesheet link of the LLMClient's Google font. */
export const GOOGLE_FONT_LINK_ID = "smarter-chat-google-font";

/**
 * The css variable of each setting of each section, by section, e.g. conversation_header's
 * background_color is --smarter-chat-header-bg.
 */
const SECTION_VARIABLES: Record<string, { prefix: string; fields: Record<string, string> }> = {
  main_container: {
    prefix: "main-container",
    fields: { background_color: "bg", color: "color", border_color: "border-color" },
  },
  conversation_header: {
    prefix: "header",
    fields: { background_color: "bg", color: "color", info_color: "info-color", border_color: "border-color" },
  },
  message_list: { prefix: "message-list", fields: { background_color: "bg", color: "color" } },
  incoming_message: {
    prefix: "incoming",
    fields: { background_color: "bg", color: "color", border_color: "border-color", link_color: "link-color" },
  },
  outgoing_message: {
    prefix: "outgoing",
    fields: { background_color: "bg", color: "color", border_color: "border-color", link_color: "link-color" },
  },
  message_input: {
    prefix: "input",
    fields: {
      background_color: "bg",
      editor_background_color: "editor-bg",
      color: "color",
      placeholder_color: "placeholder-color",
      border_color: "border-color",
    },
  },
  buttons: { prefix: "button", fields: { color: "color" } },
  typing_indicator: { prefix: "typing", fields: { color: "color" } },
};

/** The value, if it is a plain css value. */
export function safeCssValue(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!SAFE_CSS_VALUE.test(trimmed) || /[()]/.test(trimmed.replace(COLOR_FUNCTION, ""))) return null;
  return trimmed;
}

/** The url, if it is an https url that can be used in css' url(). */
export function safeImageUrl(value: string | null | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return SAFE_IMAGE_URL.test(trimmed) ? trimmed : null;
}

/** The url of the Google Fonts stylesheet of a font, or null if the name isn't a font's. */
export function googleFontUrl(name: string | null | undefined): string | null {
  if (typeof name !== "string" || !SAFE_GOOGLE_FONT.test(name.trim())) return null;
  const family = name.trim().replace(/ +/g, "+");
  return `https://fonts.googleapis.com/css2?family=${family}:wght@400;600;700&display=swap`;
}

/** The font stack: fontFamily, or the Google font, or null for chatscope's. */
export function fontFamily(styles: ChatStyles | null | undefined): string | null {
  const family = safeCssValue(styles?.font_family);
  if (family) return family;
  return googleFontUrl(styles?.google_font) ? `"${styles!.google_font!.trim()}", system-ui, sans-serif` : null;
}

/**
 * The css variables of the styles, for the chat's root element's style.
 *
 * @param styles The LLMClient's styles, or nothing.
 * @returns The variables, without those of the settings that are not set, or not valid.
 */
export function styleVariables(styles: ChatStyles | null | undefined): CSSProperties {
  const variables: Record<string, string> = {};
  if (!styles) return variables;
  const set = (name: string, value: string | null) => {
    if (value) variables[`--smarter-chat-${name}`] = value;
  };

  set("font-family", fontFamily(styles));
  set("font-size", safeCssValue(styles.font_size));
  set("border-radius", safeCssValue(styles.border_radius));

  for (const [section, { prefix, fields }] of Object.entries(SECTION_VARIABLES)) {
    const values = styles[section as keyof ChatStyles] as ChatStyleSection | null | undefined;
    if (!values || typeof values !== "object") continue;
    for (const [field, suffix] of Object.entries(fields)) {
      set(`${prefix}-${suffix}`, safeCssValue(values[field as keyof ChatStyleSection] as string | null | undefined));
    }
  }

  // the chat container is painted over the main container, in Smarter's own translucent gray. With
  // a background color of its own, the main container shows through.
  if (variables["--smarter-chat-main-container-bg"]) set("chat-container-bg", "transparent");

  // links in messages are inverted, so that they're readable on the default colors. A link color
  // of its own is displayed as is.
  for (const direction of ["incoming", "outgoing"]) {
    if (variables[`--smarter-chat-${direction}-link-color`]) set(`${direction}-link-filter`, "none");
  }

  // the background image is painted under the message list's color, which tints it: a gradient of
  // that one color is the image's top layer, and the list itself is transparent.
  const image = safeImageUrl(styles.app_background_image_url);
  if (image) {
    const tint = variables["--smarter-chat-message-list-bg"] ?? "transparent";
    set("background-image", `linear-gradient(${tint}, ${tint}), url(${JSON.stringify(image)})`);
    set("message-list-bg", "transparent");
    const size = styles.app_background_image_size ?? "cover";
    set("background-size", size);
    set("background-repeat", size === "auto" ? "repeat" : "no-repeat");
  }
  return variables as CSSProperties;
}

/**
 * Loads the Google font of the styles, once per page, with a stylesheet link in the page's head.
 *
 * @param name The font's name, from the Google Fonts catalog, or nothing.
 */
export function useGoogleFont(name: string | null | undefined): void {
  const href = googleFontUrl(name);
  useEffect(() => {
    if (!href || typeof document === "undefined") return;
    const existing = document.getElementById(GOOGLE_FONT_LINK_ID) as HTMLLinkElement | null;
    if (existing) {
      if (existing.href !== href) existing.href = href;
      return;
    }
    const link = document.createElement("link");
    link.id = GOOGLE_FONT_LINK_ID;
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }, [href]);
}
