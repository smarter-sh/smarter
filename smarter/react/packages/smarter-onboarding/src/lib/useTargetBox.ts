/**
 * The box of the element that a hint points to, kept up to date while the page scrolls, resizes or moves the
 * element, e.g. when the sidebar collapses.
 */
import { useEffect, useState } from "react";

import type { Box } from "./position";
import { isVisible } from "./targets";

/** The element's box in the window's coordinates, or null while it is off screen. */
function measureBox(target: HTMLElement): Box | null {
  if (!isVisible(target)) return null;
  const rect = target.getBoundingClientRect();
  return { top: rect.top, left: rect.left, width: rect.width, height: rect.height };
}

const sameBox = (a: Box | null, b: Box | null) =>
  a === b || (!!a && !!b && a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height);

/**
 * :param target: The element, or null.
 * :returns: Its box in the window's coordinates, or null while it is off screen.
 */
export function useTargetBox(target: HTMLElement | null): Box | null {
  // the box, and the element that it is the box of, so that another element's box is never returned.
  const [measured, setMeasured] = useState<{ target: HTMLElement | null; box: Box | null }>(() => ({
    target,
    box: target ? measureBox(target) : null,
  }));
  useEffect(() => {
    if (!target) return;
    let frame = 0;
    const measure = () => {
      const box = measureBox(target);
      setMeasured((previous) =>
        previous.target === target && sameBox(previous.box, box) ? previous : { target, box },
      );
      frame = window.requestAnimationFrame(measure);
    };
    frame = window.requestAnimationFrame(measure);
    return () => window.cancelAnimationFrame(frame);
  }, [target]);
  if (measured.target !== target) return target ? measureBox(target) : null;
  return measured.box;
}
