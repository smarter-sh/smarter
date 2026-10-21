/**
 * Pasting into the message input as plain text.
 *
 * The message input is a contenteditable element, which by default pastes the clipboard's html: text copied
 * from a chat bubble, e.g. an example prompt, would bring the bubble's fonts, colors and list bullets with it.
 * pastePlainText pastes the clipboard's text only.
 */
import type { ClipboardEvent } from "react";

/**
 * Inserts text at the caret of the focused contenteditable element, replacing the selection, and tells the
 * element's input listeners, as typing would.
 *
 * @param text - The text to insert.
 * @param doc - The document whose selection to use.
 */
export function insertPlainText(text: string, doc: Document = document): void {
  // insertText keeps the browser's undo history, and fires the input event itself.
  if (typeof doc.execCommand === "function" && doc.execCommand("insertText", false, text)) return;

  const selection = doc.getSelection();
  if (!selection || selection.rangeCount === 0) return;
  const range = selection.getRangeAt(0);
  range.deleteContents();
  const node = doc.createTextNode(text);
  range.insertNode(node);
  range.setStartAfter(node);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
  const editable = node.parentElement?.closest("[contenteditable]");
  editable?.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: text }));
}

/**
 * A paste handler that pastes the clipboard's plain text instead of its html.
 *
 * @param event - The paste event of the message input, or of an element that contains it.
 */
export function pastePlainText(event: ClipboardEvent<HTMLElement>): void {
  const text = event.clipboardData?.getData("text/plain") ?? "";
  event.preventDefault();
  if (text) insertPlainText(text, event.currentTarget.ownerDocument);
}
