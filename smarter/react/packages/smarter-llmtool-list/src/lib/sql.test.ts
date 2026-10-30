import { describe, expect, it } from "vitest";

import { formatSql } from "@/lib/sql";

describe("formatSql", () => {
  it("puts each clause on its own line, with upper-case keywords, and keeps the {name} placeholders", () => {
    expect(formatSql("select c.name from courses c where c.cost <= {max_cost} order by c.name;")).toBe(
      ["SELECT", "  c.name", "FROM", "  courses c", "WHERE", "  c.cost <= {max_cost}", "ORDER BY", "  c.name;"].join(
        "\n",
      ),
    );
  });

  it("shows a query that it can't parse as it is", () => {
    expect(formatSql("  select ( from  ")).toBe("select ( from");
  });
});
