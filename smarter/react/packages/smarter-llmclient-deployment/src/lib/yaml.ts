/**
 * A small YAML highlighter, for the LLMClient's manifest, as `smarter describe llmclient` writes it:
 * mapping keys, list items, scalars, and literal blocks (`|`, `>`). It splits each line into tokens,
 * which the page renders as text in spans, so nothing in the manifest is ever HTML.
 */

/** What a token is, which its color shows: see .yaml-* in styles.css. */
export type YamlTokenKind = "key" | "string" | "literal" | "block" | "punctuation" | "plain";

export type YamlToken = { text: string; kind: YamlTokenKind };

/** A line that starts a mapping key, optionally as a list item: `  - key: value`. */
const KEY_LINE = /^(?<indent>\s*)(?<dash>- )?(?<key>[A-Za-z_][\w-]*):(?<value>.*)$/;

/** A line that is a list item's scalar: `  - value`. */
const LIST_LINE = /^(?<indent>\s*)- (?<value>.*)$/;

/** The scalars that are colored as literals. */
const LITERALS = new Set(["true", "false", "null", "~"]);
const NUMBER = /^-?\d+(\.\d+)?$/;

/** The tokens of a scalar: its leading whitespace, then the value, colored by its kind. */
function valueTokens(value: string): YamlToken[] {
  const stripped = value.trim();
  if (!stripped) return value ? [{ text: value, kind: "plain" }] : [];
  const leading = value.slice(0, value.length - value.trimStart().length);
  let kind: YamlTokenKind = "string";
  if (LITERALS.has(stripped) || NUMBER.test(stripped)) kind = "literal";
  else if (stripped.startsWith("|") || stripped.startsWith(">")) kind = "block";
  const tokens: YamlToken[] = leading ? [{ text: leading, kind: "plain" }] : [];
  tokens.push({ text: stripped, kind });
  return tokens;
}

const indentOf = (line: string) => line.length - line.trimStart().length;

/**
 * Split YAML into lines of tokens.
 *
 * The lines of a literal block, those indented more deeply than the key that starts it, and the blank
 * lines inside it, are strings.
 *
 * @param text - The YAML.
 * @returns One array of tokens per line.
 */
export function highlightYaml(text: string): YamlToken[][] {
  const lines: YamlToken[][] = [];
  let blockIndent: number | null = null;
  for (const line of text.split("\n")) {
    const indent = indentOf(line);
    if (blockIndent !== null && (!line.trim() || indent > blockIndent)) {
      lines.push([{ text: line, kind: "string" }]);
      continue;
    }
    blockIndent = null;
    const keyLine = KEY_LINE.exec(line);
    const listLine = keyLine ? null : LIST_LINE.exec(line);
    if (keyLine?.groups) {
      const { indent: spaces, dash, key, value } = keyLine.groups;
      const tokens: YamlToken[] = spaces ? [{ text: spaces, kind: "plain" }] : [];
      if (dash) tokens.push({ text: dash, kind: "punctuation" });
      tokens.push({ text: key, kind: "key" }, { text: ":", kind: "punctuation" }, ...valueTokens(value));
      lines.push(tokens);
      const stripped = value.trim();
      if (stripped.startsWith("|") || stripped.startsWith(">")) blockIndent = indent + (dash ? 2 : 0);
    } else if (listLine?.groups) {
      const { indent: spaces, value } = listLine.groups;
      const tokens: YamlToken[] = spaces ? [{ text: spaces, kind: "plain" }] : [];
      tokens.push({ text: "- ", kind: "punctuation" }, ...valueTokens(value));
      lines.push(tokens);
    } else {
      lines.push([{ text: line, kind: "plain" }]);
    }
  }
  return lines;
}
