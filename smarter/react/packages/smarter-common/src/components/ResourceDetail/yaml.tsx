/**
 * A small YAML highlighter, for reading a manifest: keys, strings, numbers, booleans and comments, one line at a
 * time. A manifest is the YAML that the backend dumps, so its lines are simple: "key: value", "- item", or a
 * block scalar's text. Editing a manifest is the manifest editor's job, with Monaco, on the manifest's own page.
 */
import type { ReactNode } from "react";

/** The class of a scalar value, by what it looks like. */
function scalarClass(value: string): string {
  const trimmed = value.trim();
  if (/^(true|false|yes|no|null|~)$/i.test(trimmed)) return "yaml-literal";
  if (/^-?\d+(\.\d+)?([eE][-+]?\d+)?$/.test(trimmed)) return "yaml-number";
  if (/^[|>][-+]?$/.test(trimmed)) return "yaml-punctuation";
  return "yaml-string";
}

/** A value, and the comment after it, if any. */
function valueTokens(text: string, key: string): ReactNode[] {
  if (!text) return [];
  // a comment starts with " #", outside a quoted string. Manifests rarely have them after a value.
  const quoted = /^\s*(['"]).*\1\s*$/.test(text);
  const commentAt = quoted ? -1 : text.search(/\s#/);
  const value = commentAt >= 0 ? text.slice(0, commentAt) : text;
  const comment = commentAt >= 0 ? text.slice(commentAt) : "";
  const leading = value.match(/^\s*/)?.[0] ?? "";
  const tokens: ReactNode[] = [leading];
  if (value.trim()) {
    tokens.push(
      <span key={`${key}-v`} className={scalarClass(value)}>
        {value.slice(leading.length)}
      </span>,
    );
  }
  if (comment) {
    tokens.push(
      <span key={`${key}-c`} className="yaml-comment">
        {comment}
      </span>,
    );
  }
  return tokens;
}

/**
 * One line of YAML, as highlighted spans.
 *
 * @param line - The line, without its newline.
 * @param inBlock - Whether the line is part of a block scalar's text, which is a string, whatever it looks like.
 */
export function highlightYamlLine(line: string, inBlock = false): ReactNode[] {
  if (inBlock)
    return [
      <span key="b" className="yaml-string">
        {line}
      </span>,
    ];
  if (/^\s*#/.test(line))
    return [
      <span key="c" className="yaml-comment">
        {line}
      </span>,
    ];
  // "  - key: value", "key: value", "- value"
  const match = line.match(/^(\s*)(-\s+)?(?:((?:"[^"]*"|'[^']*'|[^\s#'"][^:#]*?)):(?=\s|$))?(.*)$/);
  if (!match) return [line];
  const [, indent, dash, key, rest] = match;
  const tokens: ReactNode[] = [indent];
  if (dash) {
    tokens.push(
      <span key="d" className="yaml-punctuation">
        {dash}
      </span>,
    );
  }
  if (key !== undefined) {
    tokens.push(
      <span key="k" className="yaml-key">
        {key}
      </span>,
      <span key="p" className="yaml-punctuation">
        :
      </span>,
    );
  }
  tokens.push(...valueTokens(rest, "r"));
  return tokens;
}

/** The indentation of a line, in spaces. */
const indentOf = (line: string) => line.match(/^ */)?.[0].length ?? 0;

/**
 * The lines of a YAML document, each highlighted. A block scalar's text ("key: |" and the more indented lines
 * after it) is highlighted as a string.
 */
export function highlightYaml(yaml: string): ReactNode[][] {
  const lines = yaml.replace(/\n$/, "").split("\n");
  let blockIndent: number | null = null;
  return lines.map((line) => {
    if (blockIndent !== null) {
      if (!line.trim() || indentOf(line) > blockIndent) return highlightYamlLine(line, true);
      blockIndent = null;
    }
    if (/:\s*[|>][-+]?\s*$/.test(line)) blockIndent = indentOf(line);
    return highlightYamlLine(line);
  });
}
