import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { formatDateTime } from "./formatDateTime";

describe("formatDateTime", () => {
  beforeEach(() => {
    vi.useFakeTimers({ now: new Date("2026-06-15T12:00:00Z") });
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("formats a date", () => {
    expect(formatDateTime("2026-06-01T12:00:00Z")).toBe("06/01/2026");
  });

  it("returns - for a missing or invalid date", () => {
    expect(formatDateTime(null)).toBe("-");
    expect(formatDateTime("not a date")).toBe("-");
  });

  it("formats an update relative to now", () => {
    expect(formatDateTime("2026-06-14T12:00:00Z", "relative", "2026-06-01T12:00:00Z")).toBe("1 day ago");
  });

  it("formats a relative time in the language of the page", () => {
    const lang = document.documentElement.lang;
    try {
      const spanish = "hace 1 día"; // codespell:ignore
      document.documentElement.lang = "es";
      expect(formatDateTime("2026-06-14T12:00:00Z", "relative", "2026-06-01T12:00:00Z")).toBe(spanish);
      document.documentElement.lang = "fr";
      expect(formatDateTime("2026-06-14T12:00:00Z", "relative", "2026-06-01T12:00:00Z")).toBe("il y a 1 jour");
    } finally {
      document.documentElement.lang = lang;
    }
  });

  it("says never for an update at its creation", () => {
    expect(formatDateTime("2026-06-01T12:00:02Z", "relative", "2026-06-01T12:00:00Z")).toBe("never");
  });

  it("requires a reference date for a relative date", () => {
    expect(() => formatDateTime("2026-06-01T12:00:00Z", "relative")).toThrow(/referenceValue/);
  });
});
