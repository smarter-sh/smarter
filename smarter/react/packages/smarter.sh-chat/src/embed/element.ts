/**
 * <smarter-chat>: the custom element of the embed script. It renders a Smarter chat in its own shadow root, with the
 * embed's css, so that the website's css can't change the chat, and the chat's css can't change the website.
 *
 * ```html
 * <smarter-chat chatbot="https://support.3141-5926-5359.api.example.com/" height="600px"></smarter-chat>
 * ```
 *
 * Its attributes are the options in options.ts. It is "inline" unless its mode attribute says "launcher". It renders
 * again when an attribute changes, and unmounts the chat when it leaves the page. Page scripts can open(), close()
 * and toggle() a launcher, which dispatches a "smarter-chat-toggle" event, with detail.open, when it opens or closes.
 */
import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";

import { loggerPrefix } from "@/const";
import { applyCss, embedCss, hoistFontFaces } from "./css";
import EmbedApp from "./EmbedApp";
import { OPTION_ATTRIBUTES, parseOptions, type EmbedOptionsResult } from "./options";

export const ELEMENT_NAME = "smarter-chat";
export const TOGGLE_EVENT = "smarter-chat-toggle";

export class SmarterChatElement extends HTMLElement {
  static observedAttributes = [...OPTION_ATTRIBUTES];

  #root: Root | null = null;
  #container: HTMLDivElement | null = null;
  #open: boolean | null = null;
  #lastError: string | null = null;

  /** The element's options, from its attributes. */
  get options(): EmbedOptionsResult {
    return parseOptions((name) => this.getAttribute(name), "inline");
  }

  /** Whether the launcher is open. */
  get isOpen(): boolean {
    return this.#open ?? this.options.options?.open ?? false;
  }

  connectedCallback(): void {
    let shadow = this.shadowRoot;
    if (!shadow) {
      shadow = this.attachShadow({ mode: "open" });
      const css = embedCss();
      applyCss(shadow, css);
      hoistFontFaces(css, this.ownerDocument);
    }
    this.#container = this.ownerDocument.createElement("div");
    shadow.append(this.#container);
    this.#root = createRoot(this.#container);
    this.#render();
  }

  disconnectedCallback(): void {
    this.#root?.unmount();
    this.#root = null;
    this.#container?.remove();
    this.#container = null;
  }

  attributeChangedCallback(): void {
    this.#render();
  }

  open(): void {
    this.#setOpen(true);
  }

  close(): void {
    this.#setOpen(false);
  }

  toggle(): void {
    this.#setOpen(!this.isOpen);
  }

  #setOpen(open: boolean): void {
    if (open === this.isOpen) return;
    this.#open = open;
    this.#render();
    this.dispatchEvent(new CustomEvent(TOGGLE_EVENT, { detail: { open }, bubbles: true, composed: true }));
  }

  #render(): void {
    if (!this.#root) return;
    const { options, error } = this.options;
    if (!options) {
      // once per error, rather than on every attribute change.
      if (error !== this.#lastError) console.error(`${loggerPrefix} <${ELEMENT_NAME}>: ${error}`);
      this.#lastError = error;
      this.#root.render(null);
      return;
    }
    this.#lastError = null;
    this.#root.render(
      createElement(EmbedApp, {
        options,
        open: this.isOpen,
        onOpenChange: (open: boolean) => this.#setOpen(open),
      }),
    );
  }
}

/** Defines <smarter-chat>, unless the page already has, e.g. with another copy of the embed script. */
export function defineElement(registry: CustomElementRegistry = customElements): void {
  if (!registry.get(ELEMENT_NAME)) registry.define(ELEMENT_NAME, SmarterChatElement);
}
