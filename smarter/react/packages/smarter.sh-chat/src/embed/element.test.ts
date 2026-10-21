/* eslint-disable testing-library/no-node-access, testing-library/prefer-screen-queries -- screen doesn't see into
   shadow roots, so the tests query the element's shadow root, with within() or its own methods. */
import { act, fireEvent, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { API_URL } from "@/mocks/fixtures";
import { chatHandlers } from "@/mocks/handlers";
import { server } from "@test/server";
import { ELEMENT_NAME, SmarterChatElement, TOGGLE_EVENT, defineElement } from "./element";
import { FONT_STYLE_ID, addCss } from "./css";
import { PANEL_ID } from "./EmbedApp";

const WELCOME = "Welcome to Stackademy! How can I help you today?";

/** Adds a <smarter-chat> element with the attributes to the page. */
async function chat(attributes: Record<string, string>): Promise<SmarterChatElement> {
  const element = document.createElement(ELEMENT_NAME) as SmarterChatElement;
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
  await act(async () => {
    document.body.append(element);
  });
  return element;
}

/** Queries in the element's shadow root. */
function shadow(element: SmarterChatElement) {
  return within(element.shadowRoot as unknown as HTMLElement);
}

beforeAll(() => {
  addCss("@font-face{font-family:Test;src:url(x.woff2)}.SmarterChat{color:black}");
  defineElement();
});

afterEach(async () => {
  await act(async () => {
    document.querySelectorAll(ELEMENT_NAME).forEach((element) => element.remove());
  });
});

describe("<smarter-chat>", () => {
  it("is defined once, even if the script runs twice", () => {
    const registry = { get: vi.fn(() => SmarterChatElement), define: vi.fn() } as unknown as CustomElementRegistry;
    defineElement(registry);
    expect(registry.define).not.toHaveBeenCalled();
    expect(customElements.get(ELEMENT_NAME)).toBe(SmarterChatElement);
  });

  it("renders the chat inline, in its own shadow root, with the embed's css", async () => {
    server.use(...chatHandlers);
    const element = await chat({ chatbot: API_URL, height: "500px" });
    expect(await shadow(element).findByText(WELCOME)).toBeInTheDocument();
    // the page's own queries don't see into the shadow root.
    expect(document.body.querySelector(".SmarterChat")).toBeNull();
    const style = element.shadowRoot!.querySelector("style");
    expect(style?.textContent).toContain(".SmarterChat{color:black}");
    expect(document.getElementById(FONT_STYLE_ID)?.textContent).toContain("font-family:Test");
    const inline = element.shadowRoot!.querySelector<HTMLElement>(".smarter-chat-embed-inline");
    expect(inline?.style.height).toBe("500px");
    expect(inline?.style.width).toBe("100%");
    // the sandbox mode is for the web console's workbench, not for websites.
    expect(shadow(element).queryByRole("group", { name: "Chat mode" })).not.toBeInTheDocument();
  });

  it("logs an error, once, and renders nothing, without a valid chatbot", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const element = await chat({ chatbot: "nope" });
    await act(async () => element.setAttribute("height", "300px"));
    expect(error).toHaveBeenCalledTimes(1);
    expect(error.mock.calls[0].join(" ")).toContain('"chatbot" must be');
    expect(element.shadowRoot!.querySelector(".SmarterChat")).toBeNull();
  });

  it("renders a launcher, which renders the chat only once it is opened, and keeps it when it closes", async () => {
    server.use(...chatHandlers);
    const user = userEvent.setup();
    const element = await chat({ chatbot: API_URL, mode: "launcher", label: "Ask Stanley", position: "bottom-left" });
    const view = shadow(element);
    const button = view.getByRole("button", { name: "Ask Stanley" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(element.shadowRoot!.querySelector(".smarter-chat-embed-bottom-left")).toBeInTheDocument();
    // no request until the visitor opens it: MSW would fail an unexpected one, but none is made.
    expect(element.shadowRoot!.querySelector(".SmarterChat")).toBeNull();

    const toggled = vi.fn();
    element.addEventListener(TOGGLE_EVENT, (event) => toggled((event as CustomEvent).detail.open));
    await user.click(button);
    expect(await view.findByText(WELCOME)).toBeInTheDocument();
    expect(view.getByRole("button", { name: "Close Ask Stanley" })).toHaveAttribute("aria-expanded", "true");
    expect(element.isOpen).toBe(true);

    await user.click(view.getByRole("button", { name: "Close Ask Stanley" }));
    const panel = element.shadowRoot!.getElementById(PANEL_ID);
    expect(panel).toHaveAttribute("aria-label", "Ask Stanley");
    expect(panel).not.toBeVisible();
    // still rendered, so the conversation is there when it opens again.
    expect(element.shadowRoot!.querySelector(".SmarterChat")).not.toBeNull();
    expect(toggled.mock.calls).toEqual([[true], [false]]);
  });

  it("labels the launcher in the chat's language", async () => {
    server.use(...chatHandlers);
    const user = userEvent.setup();
    const element = await chat({ chatbot: API_URL, mode: "launcher", language: "fr" });
    const view = shadow(element);
    await user.click(view.getByRole("button", { name: "Chat" }));
    expect(await view.findByText(WELCOME)).toBeInTheDocument();
    expect(view.getByRole("button", { name: "Fermer Chat" })).toBeInTheDocument();
    expect(view.getByRole("button", { name: "Démarrer un nouveau chat" })).toBeInTheDocument();
  });

  it("closes the launcher with Escape, and returns the focus to its button", async () => {
    server.use(...chatHandlers);
    const element = await chat({ chatbot: API_URL, mode: "launcher", open: "" });
    const view = shadow(element);
    await view.findByText(WELCOME);
    const panel = element.shadowRoot!.getElementById(PANEL_ID)!;
    expect(panel).toBeVisible();
    // user-event types into document.activeElement, which is the shadow root's host, so the key is fired at the panel.
    fireEvent.keyDown(panel, { key: "a" });
    expect(element.isOpen).toBe(true);
    fireEvent.keyDown(panel, { key: "Escape" });
    await waitFor(() => expect(panel).not.toBeVisible());
    expect(element.shadowRoot!.activeElement).toBe(view.getByRole("button", { name: "Chat" }));
    expect(element.isOpen).toBe(false);
  });

  it("can be opened, closed and toggled by page scripts", async () => {
    server.use(...chatHandlers);
    const element = await chat({ chatbot: API_URL, mode: "launcher" });
    await act(async () => element.open());
    expect(element.isOpen).toBe(true);
    await act(async () => element.open());
    expect(element.isOpen).toBe(true);
    await act(async () => element.toggle());
    expect(element.isOpen).toBe(false);
    await act(async () => element.close());
    expect(element.isOpen).toBe(false);
  });

  it("renders again when an attribute changes, and unmounts when it leaves the page", async () => {
    server.use(...chatHandlers);
    const element = await chat({ chatbot: API_URL });
    await shadow(element).findByText(WELCOME);
    await act(async () => element.setAttribute("height", "321px"));
    expect(element.shadowRoot!.querySelector<HTMLElement>(".smarter-chat-embed-inline")?.style.height).toBe("321px");
    await act(async () => element.remove());
    expect(element.shadowRoot!.querySelector(".SmarterChat")).toBeNull();
    // and is rendered again, in the same shadow root, when it comes back.
    await act(async () => document.body.append(element));
    await waitFor(() => expect(element.shadowRoot!.querySelectorAll(".SmarterChat")).toHaveLength(1));
    expect(element.shadowRoot!.querySelectorAll("style")).toHaveLength(1);
  });
});
