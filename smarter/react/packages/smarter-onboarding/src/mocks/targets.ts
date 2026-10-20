/**
 * Elements for tests and stories that hints can point to. jsdom has no layout, so their boxes are stubbed.
 */
import { vi } from "vitest";

import type { Box } from "../lib/position";

/** Gives the element a box, as if it were laid out on the page. */
export function stubBox(element: Element, box: Box): void {
  vi.spyOn(element, "getBoundingClientRect").mockReturnValue({
    ...box,
    x: box.left,
    y: box.top,
    right: box.left + box.width,
    bottom: box.top + box.height,
    toJSON: () => box,
  } as DOMRect);
}

const TARGET_CLASS = "smarter-onboarding-test-target";

/** Removes the elements that addTarget() added. */
export function removeTargets(): void {
  for (const element of document.querySelectorAll(`.${TARGET_CLASS}`)) element.remove();
}

/** Adds an element to the page, with a box, and returns it. */
export function addTarget(html: string, box: Box = { top: 100, left: 20, width: 120, height: 32 }): HTMLElement {
  const container = document.createElement("div");
  container.innerHTML = html;
  const element = container.firstElementChild as HTMLElement;
  element.classList.add(TARGET_CLASS);
  document.body.append(element);
  stubBox(element, box);
  return element;
}
