import { describe, expect, it } from "vitest";

import { LOG_VIEWER_SHORTCUTS, logViewerAction } from "./logViewerKeys";

describe("logViewerAction", () => {
  it("moves to the top and the bottom with Ctrl or Cmd and the arrows, Home and End, and g and G", () => {
    for (const modifier of [{ ctrlKey: true }, { metaKey: true }]) {
      expect(logViewerAction({ key: "ArrowUp", ...modifier })).toBe("top");
      expect(logViewerAction({ key: "ArrowDown", ...modifier })).toBe("bottom");
      expect(logViewerAction({ key: "ArrowLeft", ...modifier })).toBe("lineStart");
      expect(logViewerAction({ key: "ArrowRight", ...modifier })).toBe("lineEnd");
    }
    expect(logViewerAction({ key: "Home" })).toBe("top");
    expect(logViewerAction({ key: "End" })).toBe("bottom");
    expect(logViewerAction({ key: "g" })).toBe("top");
    expect(logViewerAction({ key: "G", shiftKey: true })).toBe("bottom");
  });

  it("scrolls by line, page and column", () => {
    expect(logViewerAction({ key: "ArrowUp" })).toBe("lineUp");
    expect(logViewerAction({ key: "k" })).toBe("lineUp");
    expect(logViewerAction({ key: "ArrowDown" })).toBe("lineDown");
    expect(logViewerAction({ key: "j" })).toBe("lineDown");
    expect(logViewerAction({ key: "PageUp" })).toBe("pageUp");
    expect(logViewerAction({ key: " ", shiftKey: true })).toBe("pageUp");
    expect(logViewerAction({ key: "b" })).toBe("pageUp");
    expect(logViewerAction({ key: "PageDown" })).toBe("pageDown");
    expect(logViewerAction({ key: " " })).toBe("pageDown");
    expect(logViewerAction({ key: "f" })).toBe("pageDown");
    expect(logViewerAction({ key: "ArrowLeft" })).toBe("left");
    expect(logViewerAction({ key: "h" })).toBe("left");
    expect(logViewerAction({ key: "ArrowRight" })).toBe("right");
    expect(logViewerAction({ key: "l" })).toBe("right");
    expect(logViewerAction({ key: "0" })).toBe("lineStart");
    expect(logViewerAction({ key: "$", shiftKey: true })).toBe("lineEnd");
  });

  it("toggles the viewer's modes, as k9s does", () => {
    expect(logViewerAction({ key: "w" })).toBe("wrap");
    expect(logViewerAction({ key: "s" })).toBe("follow");
    expect(logViewerAction({ key: "/" })).toBe("filter");
    expect(logViewerAction({ key: "c" })).toBe("copy");
    expect(logViewerAction({ key: "F", shiftKey: true })).toBe("fullscreen");
    expect(logViewerAction({ key: "?", shiftKey: true })).toBe("help");
    expect(logViewerAction({ key: "Escape" })).toBe("escape");
  });

  it("leaves the browser's own shortcuts, and other keys, to the browser", () => {
    expect(logViewerAction({ key: "c", ctrlKey: true })).toBeNull();
    expect(logViewerAction({ key: "c", metaKey: true })).toBeNull();
    expect(logViewerAction({ key: "w", ctrlKey: true })).toBeNull();
    expect(logViewerAction({ key: "ArrowUp", altKey: true })).toBeNull();
    expect(logViewerAction({ key: "Tab" })).toBeNull();
    expect(logViewerAction({ key: "x" })).toBeNull();
  });

  it("lists each action once", () => {
    const actions = LOG_VIEWER_SHORTCUTS.map(({ action }) => action);
    expect(new Set(actions).size).toBe(actions.length);
  });
});
