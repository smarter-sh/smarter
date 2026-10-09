import { describe, expect, it } from "vitest";

import { formatAmount, formatPeriod } from "./format";

describe("formatAmount", () => {
  it("formats costs in dollars and tokens as whole numbers", () => {
    expect(formatAmount(42.5, "cost")).toBe("$42.50");
    expect(formatAmount(1234.6, "tokens")).toBe("1,235 tokens");
  });
});

describe("formatPeriod", () => {
  const iso = "2026-06-15T13:30:00Z";

  it.each([
    ["hour", "01:30 PM"],
    ["day", "Jun 15"],
    ["week", "Week of Jun 15"],
    ["month", "Jun 2026"],
  ] as const)("labels a %s", (period, label) => {
    expect(formatPeriod(iso, period)).toBe(label);
  });
});
