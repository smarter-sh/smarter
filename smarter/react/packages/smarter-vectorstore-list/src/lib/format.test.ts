import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";

import { databaseLabel, formatCount } from "./format";

describe("format", () => {
  it("labels the database by its backend and hosting", () => {
    expect(databaseLabel(makeObject(1))).toBe("Qdrant · Self-hosted");
    expect(databaseLabel(makeObject(1, { backend: "weaviate" as never, hosting: "cloud" as never }))).toBe(
      "weaviate · cloud",
    );
  });

  it("formats a count, or zero without one", () => {
    expect(formatCount(1200)).toBe("1,200");
    expect(formatCount(null)).toBe("0");
    expect(formatCount(undefined)).toBe("0");
  });
});
