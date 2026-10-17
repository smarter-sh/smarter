/**
 * The keyboard shortcuts of the server log viewer, while it has the focus.
 *
 * They follow k9s's log view, and less and vim, where a browser allows it. A browser keeps
 * Ctrl+W and Cmd+W, which close its tab, so wrap is "w", as in k9s. macOS keeps Ctrl+Up and
 * Ctrl+Down for Mission Control, so Cmd+Up and Cmd+Down, Home and End, and g and G move to the
 * top and the bottom too.
 *
 * Smarter Chat's Console (smarter-chat/src/lib/logViewerKeys.ts) and the Prompt Passthrough's
 * Server Logs tab (smarter-prompt-passthrough/src/lib/logViewerKeys.ts) have a copy of this file,
 * because they are published separately. Keep the two the same.
 */

/** What a key does in the log viewer. */
export type LogViewerAction =
  | "top"
  | "bottom"
  | "lineUp"
  | "lineDown"
  | "pageUp"
  | "pageDown"
  | "left"
  | "right"
  | "lineStart"
  | "lineEnd"
  | "wrap"
  | "follow"
  | "filter"
  | "copy"
  | "fullscreen"
  | "help"
  | "escape";

/** The properties of a keydown event that decide its action. */
export interface LogViewerKey {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
}

/** A shortcut, for the viewer's list of shortcuts: its keys, and what it does. */
export interface LogViewerShortcut {
  keys: string[];
  action: LogViewerAction;
}

/** The shortcuts, in the order that the viewer lists them. */
export const LOG_VIEWER_SHORTCUTS: LogViewerShortcut[] = [
  { keys: ["Ctrl+↑", "Cmd+↑", "Home", "g"], action: "top" },
  { keys: ["Ctrl+↓", "Cmd+↓", "End", "G"], action: "bottom" },
  { keys: ["↑", "k"], action: "lineUp" },
  { keys: ["↓", "j"], action: "lineDown" },
  { keys: ["PgUp", "Shift+Space", "b"], action: "pageUp" },
  { keys: ["PgDn", "Space", "f"], action: "pageDown" },
  { keys: ["←", "h"], action: "left" },
  { keys: ["→", "l"], action: "right" },
  { keys: ["Ctrl+←", "Cmd+←", "0"], action: "lineStart" },
  { keys: ["Ctrl+→", "Cmd+→", "$"], action: "lineEnd" },
  { keys: ["w"], action: "wrap" },
  { keys: ["s"], action: "follow" },
  { keys: ["/"], action: "filter" },
  { keys: ["c"], action: "copy" },
  { keys: ["F", "Shift+F"], action: "fullscreen" },
  { keys: ["?"], action: "help" },
  { keys: ["Esc"], action: "escape" },
];

const PLAIN_KEYS: Record<string, LogViewerAction> = {
  ArrowUp: "lineUp",
  ArrowDown: "lineDown",
  ArrowLeft: "left",
  ArrowRight: "right",
  Home: "top",
  End: "bottom",
  PageUp: "pageUp",
  PageDown: "pageDown",
  Escape: "escape",
  g: "top",
  G: "bottom",
  k: "lineUp",
  j: "lineDown",
  h: "left",
  l: "right",
  b: "pageUp",
  f: "pageDown",
  "0": "lineStart",
  $: "lineEnd",
  w: "wrap",
  s: "follow",
  "/": "filter",
  c: "copy",
  F: "fullscreen",
  "?": "help",
};

const MODIFIED_ARROWS: Record<string, LogViewerAction> = {
  ArrowUp: "top",
  ArrowDown: "bottom",
  ArrowLeft: "lineStart",
  ArrowRight: "lineEnd",
};

/**
 * The action of a key, or null for a key that the viewer leaves to the browser, e.g. Ctrl+C,
 * which copies the selected text.
 */
export function logViewerAction({ key, ctrlKey, metaKey, altKey, shiftKey }: LogViewerKey): LogViewerAction | null {
  if (altKey) return null;
  if (ctrlKey || metaKey) return MODIFIED_ARROWS[key] ?? null;
  if (key === " ") return shiftKey ? "pageUp" : "pageDown";
  return PLAIN_KEYS[key] ?? null;
}
