import { afterEach, describe, expect, it, vi } from "vitest";

import { MAX_SAVED_LENGTH, SCREEN_KEY, loadScreen, saveScreen } from "@/lib/screen";

describe("saveScreen and loadScreen", () => {
  afterEach(() => vi.restoreAllMocks());

  it("keep the screen in the tab's sessionStorage", () => {
    expect(loadScreen()).toBeNull();
    saveScreen("\x1b[32m$\x1b[0m ls\r\n");
    expect(window.sessionStorage.getItem(SCREEN_KEY)).toBe("\x1b[32m$\x1b[0m ls\r\n");
    expect(loadScreen()).toBe("\x1b[32m$\x1b[0m ls\r\n");
  });

  it("keep none of a screen that is too long, or empty", () => {
    saveScreen("kept");
    saveScreen("x".repeat(MAX_SAVED_LENGTH + 1));
    expect(loadScreen()).toBeNull();
    saveScreen("kept");
    saveScreen("");
    expect(loadScreen()).toBeNull();
  });

  it("keep none, without failing, when the storage fails", () => {
    vi.spyOn(console, "debug").mockImplementation(() => {});
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(() => saveScreen("screen")).not.toThrow();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(loadScreen()).toBeNull();
  });
});
