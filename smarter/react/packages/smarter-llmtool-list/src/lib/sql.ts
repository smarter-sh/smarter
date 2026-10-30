/**
 * A SqlPlugin's query, formatted for reading, as Prettier's SQL plugin formats it: one clause per line, upper-case
 * keywords, two-space indents. The query's {name} placeholders, which the plugin fills in with the LLM's arguments,
 * are parameters. A query that the formatter can't parse is shown as it is.
 */
import { format } from "sql-formatter";

export function formatSql(query: string): string {
  try {
    return format(query, {
      language: "mysql",
      keywordCase: "upper",
      tabWidth: 2,
      paramTypes: { custom: [{ regex: String.raw`\{[A-Za-z_][A-Za-z0-9_]*\}` }] },
    });
  } catch {
    return query.trim();
  }
}
