/**
 * The console's frame is the theme's own layout: Keen's app layout, which the theme turns on with attributes of
 * <body>, and Bootstrap's breakpoints. The frame reads them from the theme, rather than repeating their values,
 * so that a theme that changes a variable (--bs-app-sidebar-width, --bs-breakpoint-lg, ...) changes the console.
 */
import { useEffect, useSyncExternalStore } from "react";

/**
 * The <body> attributes that turn on the theme's layout with a fixed, dark sidebar and a fixed header, as the
 * backend's templates/base.html sets them.
 */
export const APP_LAYOUT_ATTRIBUTES: Record<string, string> = {
  "data-kt-app-layout": "dark-sidebar",
  "data-kt-app-header-fixed": "true",
  "data-kt-app-sidebar-enabled": "true",
  "data-kt-app-sidebar-fixed": "true",
  "data-kt-app-sidebar-push-header": "true",
  "data-kt-app-sidebar-push-footer": "true",
};

/** The class of <body> that the theme's app layout styles. */
export const APP_BODY_CLASS = "app-default";

/** Turn on the theme's app layout while the component that calls it is mounted, e.g. the signed-in frame. */
export function useAppLayout(): void {
  useEffect(() => {
    const body = document.body;
    for (const [name, value] of Object.entries(APP_LAYOUT_ATTRIBUTES)) {
      body.setAttribute(name, value);
    }
    body.classList.add(APP_BODY_CLASS);
    return () => {
      for (const name of Object.keys(APP_LAYOUT_ATTRIBUTES)) {
        body.removeAttribute(name);
      }
      body.classList.remove(APP_BODY_CLASS);
    };
  }, []);
}

/** Bootstrap's lg breakpoint, when the theme doesn't define --bs-breakpoint-lg. */
const DEFAULT_LG_BREAKPOINT = "992px";

/** The media query of a width below the theme's lg breakpoint, where the sidebar is a drawer. */
export function belowLgQuery(): string {
  const breakpoint = getComputedStyle(document.documentElement).getPropertyValue("--bs-breakpoint-lg").trim();
  return `(max-width: calc(${breakpoint || DEFAULT_LG_BREAKPOINT} - 0.02px))`;
}

function subscribe(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const query = window.matchMedia(belowLgQuery());
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function isBelowLg(): boolean {
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia(belowLgQuery()).matches;
}

/** Whether the window is narrower than the theme's lg breakpoint. */
export function useBelowLg(): boolean {
  return useSyncExternalStore(subscribe, isBelowLg, () => false);
}

/** The theme's modes: light, dark, or the system's. */
export type ThemeMode = "light" | "dark" | "system";

/** Where the theme's own JavaScript, on the pages that Django renders, keeps the user's choice: light, dark or system. */
export const THEME_MODE_KEY = "data-bs-theme-mode";

/** Where it keeps the theme in effect, light or dark, which index.html applies before the first paint. */
export const THEME_KEY = "data-bs-theme";

function storedItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    // storage may be blocked.
    return null;
  }
}

/** The user's choice of mode, as the theme's JavaScript stored it; light by default. */
export function themeMode(): ThemeMode {
  const mode = storedItem(THEME_MODE_KEY);
  if (mode === "dark" || mode === "system") return mode;
  return "light";
}

/** The theme a mode puts in effect: the system's for "system". */
export function resolveThemeMode(mode: ThemeMode): "light" | "dark" {
  if (mode !== "system") return mode;
  if (typeof window.matchMedia !== "function") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * Choose a mode: apply its theme, and store both, as the theme's JavaScript does, so that the pages that Django
 * renders open in the same mode.
 *
 * @param mode - The mode.
 */
export function setThemeMode(mode: ThemeMode): void {
  const theme = resolveThemeMode(mode);
  document.documentElement.setAttribute(THEME_KEY, theme);
  try {
    localStorage.setItem(THEME_MODE_KEY, mode);
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    // storage may be blocked: the mode lasts until the page is reloaded.
  }
}
