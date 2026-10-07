import { describe, expect, it } from "vitest";

import { formatAmount, formatPeriod } from "./format";

describe("formatAmount", () => {
  it("formats costs as US dollars", () => {
    expect(formatAmount(1234.5, "cost")).toBe("$1,234.50");
  });

  it("formats tokens as whole numbers", () => {
    expect(formatAmount(100250.4, "tokens")).toBe("100,250 tokens");
  });
});

describe("formatPeriod", () => {
  it("labels weeks by their first day", () => {
    expect(formatPeriod("2026-06-01T12:00:00Z", "week")).toMatch(/^Week of /);
  });

  it("labels months by month and year", () => {
    expect(formatPeriod("2026-06-15T12:00:00Z", "month")).toMatch(/2026/);
  });
});
