/**
 * The layout of the chat and the Console: the width of the chat, which the user changes by dragging
 * the separator between them, whether the Console is visible, and whether its server logs' long
 * lines wrap. They are remembered in the browser's localStorage, which may be unavailable, e.g. in a private window, so they have defaults.
 */
import {
  useCallback,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type RefObject,
  type SetStateAction,
} from "react";

import { gettext } from "@smarter/common";

/** The chat's width, as a percentage of the component's width. */
export const DEFAULT_CHAT_WIDTH = 33.33;
export const MIN_CHAT_WIDTH = 20;
export const MAX_CHAT_WIDTH = 80;
/** The change in the chat's width, in percent, for each arrow key press on the separator. */
export const KEYBOARD_STEP = 5;

export const CHAT_WIDTH_STORAGE_KEY = "smarter-chat.chat-width";
export const CONSOLE_VISIBLE_STORAGE_KEY = "smarter-chat.console-visible";
export const LOG_WRAP_STORAGE_KEY = "smarter-chat.log-wrap";

export function clampChatWidth(width: number): number {
  return Math.min(MAX_CHAT_WIDTH, Math.max(MIN_CHAT_WIDTH, width));
}

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // not remembered, e.g. in a private window.
  }
}

/** A state that the browser remembers. */
function useStoredState<T>(key: string, parse: (stored: string | null) => T, serialize: (value: T) => string) {
  const [value, setValue] = useState<T>(() => parse(readStorage(key)));
  const setStoredValue = useCallback(
    (action: SetStateAction<T>) => {
      setValue((previous) => {
        const next = typeof action === "function" ? (action as (previous: T) => T)(previous) : action;
        writeStorage(key, serialize(next));
        return next;
      });
    },
    [key, serialize],
  );
  return [value, setStoredValue] as const;
}

function parseChatWidth(stored: string | null): number {
  const width = Number(stored);
  return stored && Number.isFinite(width) ? clampChatWidth(width) : DEFAULT_CHAT_WIDTH;
}

function parseVisible(stored: string | null): boolean {
  return stored !== "false";
}

/** Whether the Console is visible. It is, until the user hides it. */
export function useConsoleVisible() {
  return useStoredState(CONSOLE_VISIBLE_STORAGE_KEY, parseVisible, String);
}

/** Whether the server logs' long lines wrap. They don't, until the user wraps them: they scroll. */
export function useLogWrap() {
  return useStoredState(LOG_WRAP_STORAGE_KEY, (stored) => stored === "true", String);
}

/**
 * The chat's width, and the props of the separator that resizes it. The separator is a focusable
 * "separator", whose value is the chat's width: drag it, or use the arrow, Home and End keys.
 * Double-click it to restore the default width.
 */
export function useChatWidth(containerRef: RefObject<HTMLElement | null>) {
  const [chatWidth, setChatWidth] = useStoredState(CHAT_WIDTH_STORAGE_KEY, parseChatWidth, String);
  const dragging = useRef(false);

  const widthAt = (clientX: number): number | null => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return null;
    return clampChatWidth(((clientX - rect.left) / rect.width) * 100);
  };

  const separatorProps = {
    role: "separator",
    tabIndex: 0,
    "aria-orientation": "vertical" as const,
    "aria-label": gettext("Resize the chat and the Console"),

    "aria-valuenow": Math.round(chatWidth),
    "aria-valuemin": MIN_CHAT_WIDTH,
    "aria-valuemax": MAX_CHAT_WIDTH,
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      dragging.current = true;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      event.preventDefault();
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      if (!dragging.current) return;
      const width = widthAt(event.clientX);
      if (width !== null) setChatWidth(width);
    },
    onPointerUp: (event: PointerEvent<HTMLElement>) => {
      dragging.current = false;
      event.currentTarget.releasePointerCapture?.(event.pointerId);
    },
    onDoubleClick: () => setChatWidth(DEFAULT_CHAT_WIDTH),
    onKeyDown: (event: KeyboardEvent<HTMLElement>) => {
      const keys: Record<string, (width: number) => number> = {
        ArrowLeft: (width) => width - KEYBOARD_STEP,
        ArrowRight: (width) => width + KEYBOARD_STEP,
        Home: () => MIN_CHAT_WIDTH,
        End: () => MAX_CHAT_WIDTH,
      };
      const change = keys[event.key];
      if (!change) return;
      event.preventDefault();
      setChatWidth((width) => clampChatWidth(change(width)));
    },
  };

  return { chatWidth, separatorProps };
}
