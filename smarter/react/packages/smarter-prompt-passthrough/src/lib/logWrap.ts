/**
 * Whether the server logs' long lines wrap, as the user last chose, in this browser.
 *
 * The choice is stored under the key of Smarter Chat's Console (smarter-chat/src/lib/layout.ts),
 * so that the Console and the Prompt Passthrough's Server Logs tab, which are both in the web
 * console, wrap alike.
 */
import { useCallback, useState, type SetStateAction } from "react";

export const LOG_WRAP_STORAGE_KEY = "smarter-chat.log-wrap";

function readWrap(): boolean {
  try {
    return window.localStorage.getItem(LOG_WRAP_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeWrap(wrap: boolean) {
  try {
    window.localStorage.setItem(LOG_WRAP_STORAGE_KEY, String(wrap));
  } catch {
    // e.g. storage is disabled. The choice lasts until the page is reloaded.
  }
}

/** Whether long lines wrap. They don't, until the user wraps them: they scroll. */
export function useLogWrap() {
  const [wrap, setWrap] = useState(readWrap);
  const setStoredWrap = useCallback((action: SetStateAction<boolean>) => {
    setWrap((previous) => {
      const next = typeof action === "function" ? action(previous) : action;
      writeWrap(next);
      return next;
    });
  }, []);
  return [wrap, setStoredWrap] as const;
}
