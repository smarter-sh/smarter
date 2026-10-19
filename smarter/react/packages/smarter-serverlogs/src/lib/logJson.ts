/**
 * The JSON of a server log record, as blocks that the server log viewer can collapse.
 *
 * Many records end with pretty-printed JSON, e.g. a prompt's request and response, which can be
 * hundreds of lines long. A block is a line that ends with "{" or "[", the lines inside it, and the
 * line that closes it, as JSON.stringify(value, null, 2) and Python's json.dumps(value, indent=2)
 * print them. Blocks can be nested. Brackets inside strings don't count. JSON on a single line is
 * not a block, nor is a bracket that never closes, e.g. in a record that was cut short.
 *
 * The record is split into lines after its ANSI colors are parsed, because a color can span lines.
 */
import { parseAnsi, type AnsiSegment } from "./ansi";

/** One line of a record: its styled text, without the newline. */
export type LogLineSegments = AnsiSegment[];

/** A line, or a block of JSON, of a record. */
export type LogNode =
  | { kind: "line"; segments: LogLineSegments }
  | { kind: "block"; open: LogLineSegments; children: LogNode[]; close: LogLineSegments; lines: number };

function lineText(segments: LogLineSegments): string {
  return segments.map((segment) => segment.text).join("");
}

/** The record's lines, each with its styled text. */
export function logLines(message: string): LogLineSegments[] {
  const lines: LogLineSegments[] = [[]];
  for (const segment of parseAnsi(message)) {
    segment.text.split("\n").forEach((text, index) => {
      if (index > 0) lines.push([]);
      if (text) lines[lines.length - 1].push({ text, style: segment.style });
    });
  }
  return lines;
}

/** The change of the bracket depth over a line: its "{" and "[", less its "}" and "]", outside strings. */
export function bracketDepthChange(text: string): number {
  let depth = 0;
  let inString = false;
  let escaped = false;
  for (const character of text) {
    if (inString) {
      if (escaped) escaped = false;
      else if (character === "\\") escaped = true;
      else if (character === '"') inString = false;
    } else if (character === '"') inString = true;
    else if (character === "{" || character === "[") depth += 1;
    else if (character === "}" || character === "]") depth -= 1;
  }
  return depth;
}

function opensBlock(text: string): boolean {
  const trimmed = text.trimEnd();
  return (trimmed.endsWith("{") || trimmed.endsWith("[")) && bracketDepthChange(trimmed) > 0;
}

/** The index of the line that closes the block that the line at start opens, or -1 if none does. */
function closingLine(texts: string[], start: number): number {
  let depth = bracketDepthChange(texts[start]);
  for (let index = start + 1; index < texts.length; index += 1) {
    depth += bracketDepthChange(texts[index]);
    if (depth <= 0) return index;
  }
  return -1;
}

function nodes(lines: LogLineSegments[], texts: string[]): LogNode[] {
  const result: LogNode[] = [];
  let index = 0;
  while (index < lines.length) {
    const close = opensBlock(texts[index]) ? closingLine(texts, index) : -1;
    if (close > index + 1) {
      result.push({
        kind: "block",
        open: lines[index],
        children: nodes(lines.slice(index + 1, close), texts.slice(index + 1, close)),
        close: lines[close],
        lines: close - index - 1,
      });
      index = close + 1;
    } else {
      result.push({ kind: "line", segments: lines[index] });
      index += 1;
    }
  }
  return result;
}

/** The record's lines and blocks of JSON. */
export function logNodes(message: string): LogNode[] {
  const lines = logLines(message);
  return nodes(lines, lines.map(lineText));
}

/** Whether a record has a block of JSON. */
export function hasJsonBlock(nodesOfRecord: LogNode[]): boolean {
  return nodesOfRecord.some((node) => node.kind === "block");
}
