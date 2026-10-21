/**
 * The embed script's script tag, and window.SmarterChatConfig, each add a <smarter-chat> element to the page:
 *
 * ```html
 * <script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
 *   data-chatbot="https://support.3141-5926-5359.api.example.com/" async></script>
 * ```
 *
 * or, where a script tag's attributes can't be set, e.g. in Google Tag Manager, or by a CMS that adds its scripts
 * itself, a configuration object, or an array of them, set before the script runs:
 *
 * ```js
 * window.SmarterChatConfig = { chatbot: "https://support.3141-5926-5359.api.example.com/", position: "bottom-left" };
 * ```
 *
 * The element is a launcher in the page's body, unless the configuration has a "target", the css selector of an
 * element of the page, in which the chat is rendered inline. A chatbot is added once: a page that runs the script
 * again, e.g. a single-page app, or a tag manager that fires twice, doesn't add a second launcher.
 */
import { loggerPrefix } from "@/const";
import { ELEMENT_NAME } from "./element";
import { configAttributes } from "./options";

/** The attribute that marks the elements that the script added, with their chatbot's url. */
export const AUTO_ATTRIBUTE = "data-smarter-chat-auto";

export type EmbedConfig = Record<string, unknown>;

declare global {
  interface Window {
    SmarterChatConfig?: EmbedConfig | EmbedConfig[];
  }
}

/** The configurations of the script tag's data- attributes and of window.SmarterChatConfig, as attributes. */
export function configurations(
  script: Element | null | undefined,
  globalConfig: EmbedConfig | EmbedConfig[] | null | undefined,
): Record<string, string>[] {
  const result: Record<string, string>[] = [];
  if (script instanceof HTMLElement && script.dataset.chatbot) {
    result.push(configAttributes({ ...script.dataset }));
  }
  for (const config of [globalConfig ?? []].flat()) {
    if (config && typeof config === "object") result.push(configAttributes(config));
  }
  return result;
}

/**
 * Adds a <smarter-chat> element for a configuration, unless the page has one for its chatbot already.
 *
 * @returns The new element, or null if none was added.
 */
export function mountChat(attributes: Record<string, string>, doc: Document = document): HTMLElement | null {
  const { target: selector, ...rest } = attributes;
  const chatbot = rest.chatbot ?? "";
  const existing = [...doc.querySelectorAll(`${ELEMENT_NAME}[${AUTO_ATTRIBUTE}]`)].find(
    (element) => element.getAttribute(AUTO_ATTRIBUTE) === chatbot,
  );
  if (existing) return null;
  let parent: Element | null = doc.body;
  if (selector) {
    try {
      parent = doc.querySelector(selector);
    } catch {
      parent = null;
    }
    if (!parent) {
      console.error(`${loggerPrefix} SmarterChatConfig.target: no element matches ${JSON.stringify(selector)}.`);
      return null;
    }
  }
  const element = doc.createElement(ELEMENT_NAME);
  element.setAttribute("mode", rest.mode ?? (selector ? "inline" : "launcher"));
  for (const [name, value] of Object.entries(rest)) {
    if (/^[a-z][a-z0-9-]*$/.test(name)) element.setAttribute(name, value);
  }
  element.setAttribute(AUTO_ATTRIBUTE, chatbot);
  parent!.append(element);
  return element;
}

/** Adds the configurations' elements once the page's body exists. */
export function autoMount(
  script: Element | null | undefined,
  globalConfig: EmbedConfig | EmbedConfig[] | null | undefined,
  doc: Document = document,
): void {
  const configs = configurations(script, globalConfig);
  if (configs.length === 0) return;
  const mountAll = () => configs.forEach((attributes) => mountChat(attributes, doc));
  if (doc.body) mountAll();
  else doc.addEventListener("DOMContentLoaded", mountAll, { once: true });
}
