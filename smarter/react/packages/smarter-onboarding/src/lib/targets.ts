/**
 * Finding the elements that hints point to: an element marked with data-smarter-onboarding, or any css
 * selector, that is on screen.
 */
import { ONBOARDING_TARGET_ATTRIBUTE } from "./const";

/** The css selector of the element marked data-smarter-onboarding="<name>". */
export function onboardingSelector(name: string): string {
  return `[${ONBOARDING_TARGET_ATTRIBUTE}="${name}"]`;
}

/**
 * Whether an element is on screen: it has a size, and neither it nor a parent is hidden, inert, or hidden
 * from assistive technology, as the workbench's Console is while it is closed.
 */
export function isVisible(element: Element): boolean {
  const rect = element.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return false;
  if (element.closest("[hidden], [inert], [aria-hidden='true']")) return false;
  return getComputedStyle(element).visibility !== "hidden";
}

/** The first element that matches the selector and is on screen, or null. */
export function findTarget(selector: string, root: ParentNode = document): HTMLElement | null {
  for (const element of root.querySelectorAll<HTMLElement>(selector)) {
    if (isVisible(element)) return element;
  }
  return null;
}

/**
 * Waits until the check returns something, e.g. an element that has come on screen, or true once the welcome
 * dialog has closed. It checks a few times a second, because a page can change without any change to the
 * document, e.g. when the sidebar slides open.
 *
 * :param check: Returns the value, or null or false to keep waiting.
 * :param options.timeout: How long to wait, in milliseconds. By default, for as long as the page is open.
 * :param options.signal: Stops waiting, e.g. when the component that waits unmounts.
 * :returns: The value, or null after the timeout, or when the signal aborts.
 */
export function waitUntil<T>(
  check: () => T | null | false,
  { timeout = Infinity, signal }: { timeout?: number; signal?: AbortSignal } = {},
): Promise<T | null> {
  return new Promise((resolve) => {
    const first = check();
    if (first || signal?.aborted) {
      resolve(first || null);
      return;
    }
    const started = Date.now();
    const stop = (value: T | null) => {
      window.clearInterval(interval);
      signal?.removeEventListener("abort", onAbort);
      resolve(value);
    };
    const onAbort = () => stop(null);
    const interval = window.setInterval(() => {
      const value = check();
      if (value) stop(value);
      else if (Date.now() - started >= timeout) stop(null);
    }, 250);
    signal?.addEventListener("abort", onAbort);
  });
}

/**
 * Waits for an element that matches the selector to be on screen, e.g. a row of a list that is still
 * loading.
 *
 * :param selector: The css selector.
 * :param options.timeout: How long to wait, in milliseconds.
 * :param options.signal: Stops waiting.
 * :returns: The element, or null after the timeout, or when the signal aborts.
 */
export function waitForTarget(
  selector: string,
  { timeout = 15000, signal }: { timeout?: number; signal?: AbortSignal } = {},
): Promise<HTMLElement | null> {
  return waitUntil(() => findTarget(selector), { timeout, signal });
}
