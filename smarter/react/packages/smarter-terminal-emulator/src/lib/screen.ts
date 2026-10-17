/**
 * The terminal's screen and scrollback, kept across a reload, or a visit to another page and back,
 * in the browser tab's sessionStorage.
 *
 * Only what was drawn is kept: the shell that drew it ended when the page was left. The terminal
 * redraws it, says so, and then starts a new session below it. sessionStorage belongs to the tab
 * and this site, and is cleared when the tab is closed. What the screen showed, e.g. the output of
 * `env`, can include credentials, so it is never kept anywhere longer lived.
 */

export const SCREEN_KEY = "smarter-terminal.screen";

/** The most lines of scrollback that are kept. */
export const MAX_SAVED_LINES = 5000;

/** The longest screen that is kept, in characters: sessionStorage holds about 5 MB per site. */
export const MAX_SAVED_LENGTH = 2_000_000;

/** Keep the screen, or, if it is too long, keep none. Storage that fails, e.g. when it is full or blocked, keeps none. */
export function saveScreen(screen: string): void {
  try {
    if (!screen || screen.length > MAX_SAVED_LENGTH) {
      window.sessionStorage.removeItem(SCREEN_KEY);
      return;
    }
    window.sessionStorage.setItem(SCREEN_KEY, screen);
  } catch (error) {
    console.debug("saveScreen() could not keep the terminal's screen:", error);
  }
}

/** The screen that was kept, if any. */
export function loadScreen(): string | null {
  try {
    return window.sessionStorage.getItem(SCREEN_KEY);
  } catch {
    return null;
  }
}
