import type { ClipboardEvent } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { insertPlainText, pastePlainText } from "./paste";

// a contenteditable element with the caret at the end of its text.
function editor(html = "") {
  const element = document.createElement("div");
  element.setAttribute("contenteditable", "true");
  element.innerHTML = html;
  document.body.appendChild(element);
  const range = document.createRange();
  range.selectNodeContents(element);
  range.collapse(false);
  const selection = document.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(range);
  return element;
}

function pasteEvent(target: HTMLElement, data: Record<string, string>) {
  return {
    clipboardData: { getData: (type: string) => data[type] ?? "" },
    currentTarget: target,
    preventDefault: vi.fn(),
  } as unknown as ClipboardEvent<HTMLElement> & { preventDefault: ReturnType<typeof vi.fn> };
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("pastePlainText", () => {
  it("pastes the clipboard's text, without its html", () => {
    const element = editor("Hi ");
    const event = pasteEvent(element, {
      "text/plain": "Derive the quadratic formula.",
      "text/html": '<ul><li style="font-family: cursive">Derive the quadratic formula.</li></ul>',
    });
    pastePlainText(event);
    expect(event.preventDefault).toHaveBeenCalled();
    expect(element.innerHTML).toBe("Hi Derive the quadratic formula.");
  });

  it("tells the input's listeners, as typing would", () => {
    const element = editor();
    const onInput = vi.fn();
    element.addEventListener("input", onInput);
    pastePlainText(pasteEvent(element, { "text/plain": "2 + 2" }));
    expect(onInput).toHaveBeenCalledTimes(1);
    expect(element).toHaveTextContent("2 + 2");
  });

  it("pastes nothing when the clipboard has no text, e.g. an image", () => {
    const element = editor("Hi");
    const event = pasteEvent(element, { "text/html": "<img src='x.png'>" });
    pastePlainText(event);
    expect(event.preventDefault).toHaveBeenCalled();
    expect(element.innerHTML).toBe("Hi");
  });
});

describe("insertPlainText", () => {
  it("uses the browser's insertText command where there is one", () => {
    const element = editor();
    const execCommand = vi.fn(() => true);
    Object.defineProperty(document, "execCommand", { value: execCommand, configurable: true });
    insertPlainText("hello");
    expect(execCommand).toHaveBeenCalledWith("insertText", false, "hello");
    expect(element).toBeEmptyDOMElement();
    delete (document as unknown as Record<string, unknown>).execCommand;
  });

  it("replaces the selection", () => {
    const element = editor("old");
    const range = document.createRange();
    range.selectNodeContents(element);
    document.getSelection()!.removeAllRanges();
    document.getSelection()!.addRange(range);
    insertPlainText("new");
    expect(element).toHaveTextContent("new");
  });

  it("does nothing without a selection", () => {
    const element = editor("Hi");
    document.getSelection()!.removeAllRanges();
    insertPlainText("x");
    expect(element).toHaveTextContent("Hi");
  });
});
