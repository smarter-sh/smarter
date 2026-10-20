import { describe, expect, it } from "vitest";

import { ARROW_INSET, GAP, MARGIN, arrowOffset, padBox, placeNote } from "@/lib/position";

const note = { width: 300, height: 120 };
const viewport = { width: 1200, height: 800 };

describe("placeNote", () => {
  it("puts the note to the right of an element with room there, e.g. a sidebar link", () => {
    const target = { top: 200, left: 20, width: 200, height: 40 };
    expect(placeNote(target, note, viewport)).toEqual({ placement: "right", top: 160, left: 220 + GAP });
  });

  it("puts it below, above or to the left when the right has no room", () => {
    const below = { top: 100, left: 1000, width: 180, height: 40 };
    expect(placeNote(below, note, viewport).placement).toBe("bottom");
    const above = { top: 700, left: 1000, width: 180, height: 40 };
    expect(placeNote(above, note, viewport).placement).toBe("top");
    const left = { top: 0, left: 900, width: 280, height: 800 };
    expect(placeNote(left, note, viewport)).toEqual({ placement: "left", top: 340, left: 900 - GAP - 300 });
  });

  it("keeps the note inside the window when nothing fits", () => {
    const huge = { top: 0, left: 0, width: 1200, height: 800 };
    expect(placeNote(huge, note, viewport)).toEqual({
      placement: "bottom",
      top: viewport.height - note.height - MARGIN,
      left: 450,
    });
  });
});

describe("padBox", () => {
  it("grows the box on every side", () => {
    expect(padBox({ top: 10, left: 10, width: 100, height: 20 }, 6)).toEqual({
      top: 4,
      left: 4,
      width: 112,
      height: 32,
    });
  });
});

describe("arrowOffset", () => {
  const size = { width: 300, height: 120 };

  it("points across from the element's middle, along the side that faces it", () => {
    const target = { top: 200, left: 20, width: 200, height: 40 };
    expect(arrowOffset(target, { top: 180, left: 236 }, size, "right")).toBe(40);
    expect(arrowOffset(target, { top: 256, left: 0 }, size, "bottom")).toBe(120);
  });

  it("stays clear of the note's corners", () => {
    const target = { top: 0, left: 0, width: 20, height: 20 };
    expect(arrowOffset(target, { top: 100, left: 40 }, size, "right")).toBe(ARROW_INSET);
    expect(arrowOffset(target, { top: 40, left: -500 }, size, "top")).toBe(size.width - ARROW_INSET);
  });
});
