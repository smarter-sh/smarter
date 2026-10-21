import { afterEach, describe, expect, it, vi } from "vitest";

import { AUTO_ATTRIBUTE, autoMount, configurations, mountChat } from "./autoMount";

const CHATBOT = "https://support.3141-5926-5359.api.example.com/";

function script(data: Record<string, string>): HTMLScriptElement {
  const element = document.createElement("script");
  for (const [name, value] of Object.entries(data)) element.setAttribute(`data-${name}`, value);
  return element;
}

// the elements stay undefined: these tests are about where they are added, with which attributes.
afterEach(() => {
  document.body.innerHTML = "";
});

describe("configurations", () => {
  it("reads the script tag's data- attributes, and window.SmarterChatConfig, an object or an array", () => {
    expect(configurations(script({ chatbot: CHATBOT, "api-key": "k", position: "bottom-left" }), null)).toEqual([
      { chatbot: CHATBOT, "api-key": "k", position: "bottom-left" },
    ]);
    expect(configurations(null, { chatbot: CHATBOT, sessionCookieName: "s" })).toEqual([
      { chatbot: CHATBOT, "session-cookie-name": "s" },
    ]);
    expect(configurations(script({ chatbot: "a" }), [{ chatbot: "b" }, null as never, { chatbot: "c" }])).toEqual([
      { chatbot: "a" },
      { chatbot: "b" },
      { chatbot: "c" },
    ]);
  });

  it("ignores a script tag without data-chatbot, e.g. one that only loads the script", () => {
    expect(configurations(script({ position: "bottom-left" }), undefined)).toEqual([]);
  });
});

describe("mountChat", () => {
  it("adds a launcher to the body", () => {
    const element = mountChat({ chatbot: CHATBOT, "api-key": "k", "bad name": "x" });
    expect(element?.parentElement).toBe(document.body);
    expect(element?.getAttribute("mode")).toBe("launcher");
    expect(element?.getAttribute("api-key")).toBe("k");
    expect(element?.getAttribute(AUTO_ATTRIBUTE)).toBe(CHATBOT);
    expect(element?.hasAttribute("bad name")).toBe(false);
  });

  it("adds a chatbot once", () => {
    expect(mountChat({ chatbot: CHATBOT })).not.toBeNull();
    expect(mountChat({ chatbot: CHATBOT })).toBeNull();
    expect(document.querySelectorAll("smarter-chat")).toHaveLength(1);
  });

  it("renders inline in its target", () => {
    document.body.innerHTML = '<main><div id="chat"></div></main>';
    const element = mountChat({ chatbot: CHATBOT, target: "#chat" });
    expect(element?.parentElement?.id).toBe("chat");
    expect(element?.getAttribute("mode")).toBe("inline");
    expect(element?.hasAttribute("target")).toBe(false);
    expect(
      mountChat({ chatbot: "https://other.example.com/", target: "#chat", mode: "launcher" })?.getAttribute("mode"),
    ).toBe("launcher");
  });

  it("logs an error when its target isn't in the page, or isn't a selector", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(mountChat({ chatbot: CHATBOT, target: "#missing" })).toBeNull();
    expect(mountChat({ chatbot: CHATBOT, target: "[[" })).toBeNull();
    expect(error).toHaveBeenCalledTimes(2);
  });
});

describe("autoMount", () => {
  it("adds the chats now, if the body exists", () => {
    autoMount(script({ chatbot: CHATBOT }), { chatbot: "https://other.example.com/" });
    expect(document.querySelectorAll("smarter-chat")).toHaveLength(2);
  });

  it("does nothing without a configuration", () => {
    autoMount(null, undefined);
    expect(document.querySelectorAll("smarter-chat")).toHaveLength(0);
  });

  it("waits for the body, when the script runs in the head", () => {
    const doc = document.implementation.createHTMLDocument("");
    doc.documentElement.removeChild(doc.body);
    autoMount(null, { chatbot: CHATBOT }, doc);
    expect(doc.querySelector("smarter-chat")).toBeNull();
    doc.documentElement.append(doc.createElement("body"));
    doc.dispatchEvent(new Event("DOMContentLoaded"));
    expect(doc.body.querySelector("smarter-chat")).not.toBeNull();
  });
});
