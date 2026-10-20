/**
 * Placing a hint's note beside the element that it points to.
 */
export interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

export type Placement = "right" | "bottom" | "top" | "left";

/** The space between the element and the note, and between the note and the edge of the window. */
export const GAP = 16;
export const MARGIN = 8;

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, Math.max(min, max)));

/**
 * Where the note goes: to the right of the element, or below, above or to its left, whichever is the first
 * with room for it, and below when none is. The note is kept inside the window.
 *
 * :param target: The element's box, in the window's coordinates.
 * :param note: The note's width and height.
 * :param viewport: The window's width and height.
 * :returns: The note's top and left, and its side of the element.
 */
export function placeNote(
  target: Box,
  note: { width: number; height: number },
  viewport: { width: number; height: number },
): { top: number; left: number; placement: Placement } {
  const centeredTop = target.top + target.height / 2 - note.height / 2;
  const centeredLeft = target.left + target.width / 2 - note.width / 2;
  const candidates: { placement: Placement; top: number; left: number; fits: boolean }[] = [
    {
      placement: "right",
      top: centeredTop,
      left: target.left + target.width + GAP,
      fits: target.left + target.width + GAP + note.width + MARGIN <= viewport.width,
    },
    {
      placement: "bottom",
      top: target.top + target.height + GAP,
      left: centeredLeft,
      fits: target.top + target.height + GAP + note.height + MARGIN <= viewport.height,
    },
    {
      placement: "top",
      top: target.top - GAP - note.height,
      left: centeredLeft,
      fits: target.top - GAP - note.height >= MARGIN,
    },
    {
      placement: "left",
      top: centeredTop,
      left: target.left - GAP - note.width,
      fits: target.left - GAP - note.width >= MARGIN,
    },
  ];
  const chosen = candidates.find((candidate) => candidate.fits) ?? candidates[1];
  return {
    placement: chosen.placement,
    top: clamp(chosen.top, MARGIN, viewport.height - note.height - MARGIN),
    left: clamp(chosen.left, MARGIN, viewport.width - note.width - MARGIN),
  };
}

/** The element's box, grown by the padding on every side, for the ring around it. */
export function padBox(box: Box, padding: number): Box {
  return {
    top: box.top - padding,
    left: box.left - padding,
    width: box.width + 2 * padding,
    height: box.height + 2 * padding,
  };
}

/** The arrow's distance from the end of the note's side, where it stays clear of the note's rounded corners. */
export const ARROW_INSET = 18;

/**
 * Where the note's arrow goes along the side that faces the element: across from the element's middle, so that
 * it points at it, even when the note has been moved to stay inside the window.
 *
 * :param target: The element's box.
 * :param note: The note's top and left.
 * :param size: The note's width and height.
 * :param placement: The note's side of the element.
 * :returns: The arrow's distance from the top of the note, for a note to the right or the left of the element,
 *   or from its left, for a note below or above it.
 */
export function arrowOffset(
  target: Box,
  note: { top: number; left: number },
  size: { width: number; height: number },
  placement: Placement,
): number {
  const sideways = placement === "left" || placement === "right";
  const along = sideways ? target.top + target.height / 2 - note.top : target.left + target.width / 2 - note.left;
  return clamp(along, ARROW_INSET, (sideways ? size.height : size.width) - ARROW_INSET);
}
