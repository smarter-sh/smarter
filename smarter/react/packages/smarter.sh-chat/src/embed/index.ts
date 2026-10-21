/**
 * The embed script, dist/embed.js: Smarter Chat for any web page, without a bundler, from one script tag.
 *
 * ```html
 * <script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
 *   data-chatbot="https://support.3141-5926-5359.api.example.com/" async></script>
 * ```
 *
 * It is a single classic script, built with `npm run build:embed` (vite build --mode embed), that includes React,
 * React DOM, Smarter Chat and its css, so that WordPress, Drupal, Shopify, Google Tag Manager and static site
 * generators can all add a chat the same way. Mermaid, which only diagrams need, is a separate build in
 * embed/mermaid/, and KaTeX's fonts are in embed/katex/fonts/, beside it. See vite.config.ts.
 *
 * Running it:
 *
 * 1. remembers its own url, to find those files (assets.ts),
 * 2. defines the <smarter-chat> element (element.ts), which pages can also use directly,
 * 3. adds a launcher for its data-chatbot attribute, and for window.SmarterChatConfig (autoMount.ts),
 * 4. sets window.SmarterChat, with which page scripts can open and close the launchers.
 */
import { projectVersion } from "@/const";
import { captureBaseUrl } from "./assets";
import { ELEMENT_NAME, defineElement, type SmarterChatElement } from "./element";
import { autoMount, type EmbedConfig, mountChat } from "./autoMount";
import { configAttributes } from "./options";
import "./styles.css";

/** The api of window.SmarterChat. */
export interface SmarterChatEmbedApi {
  version: string;
  /** Opens the launchers, or the launcher of one chatbot, by its url. */
  open: (chatbot?: string) => void;
  close: (chatbot?: string) => void;
  toggle: (chatbot?: string) => void;
  /** Adds a chat to the page, as window.SmarterChatConfig does. */
  mount: (config: EmbedConfig) => HTMLElement | null;
}

declare global {
  interface Window {
    SmarterChat?: SmarterChatEmbedApi;
  }
}

function launchers(chatbot?: string): SmarterChatElement[] {
  return [...document.querySelectorAll<SmarterChatElement>(ELEMENT_NAME)].filter(
    (element) =>
      element.options.options?.mode === "launcher" && (!chatbot || element.options.options.chatbot.startsWith(chatbot)),
  );
}

captureBaseUrl(document.currentScript);
defineElement();

window.SmarterChat = {
  version: projectVersion,
  open: (chatbot) => launchers(chatbot).forEach((element) => element.open()),
  close: (chatbot) => launchers(chatbot).forEach((element) => element.close()),
  toggle: (chatbot) => launchers(chatbot).forEach((element) => element.toggle()),
  mount: (config) => mountChat(configAttributes(config)),
};

autoMount(document.currentScript, window.SmarterChatConfig);
