/**
 * ANSI escape codes, as the server's log records have them, e.g. "\x1b[1;34m...\x1b[0m".
 *
 * The text of a log record is split into segments, each with the color and the emphasis that its
 * SGR (Select Graphic Rendition) codes give it, so that the Console displays the records as the
 * Smarter web console's log viewer (smarter-terminal-emulator, an xterm.js terminal) does. Other
 * escape sequences, e.g. cursor movements, are removed.
 */
import type { CSSProperties } from "react";

/** The xterm.js theme of smarter-terminal-emulator, by ANSI color number: 0-7, then bright 8-15. */
export const ANSI_PALETTE = [
  "#1b1f24", // black
  "#ff8f8f", // red
  "#7bd88f", // green
  "#ffd580", // yellow
  "#78dce8", // blue
  "#c792ea", // magenta
  "#89ddff", // cyan
  "#d9e1ea", // white
  "#5c6773", // bright black
  "#ff8f8f", // bright red
  "#7bd88f", // bright green
  "#ffd580", // bright yellow
  "#89ddff", // bright blue
  "#d8b4ff", // bright magenta
  "#89ddff", // bright cyan
  "#ffffff", // bright white
];

/** The text style that SGR codes set. */
export interface AnsiStyle {
  color?: string;
  backgroundColor?: string;
  bold?: boolean;
  dim?: boolean;
  italic?: boolean;
  underline?: boolean;
}

/** A run of text, with its style. */
export interface AnsiSegment {
  text: string;
  style: AnsiStyle;
}

// eslint-disable-next-line no-control-regex
const ESCAPE_SEQUENCE = /\x1b\[([0-9;?]*)([A-Za-z])|\x1b[@-Z\\-_]/g;

/** A 256 color palette color: the 16 ANSI colors, a 6x6x6 color cube, then 24 grays. */
function color256(n: number): string | undefined {
  if (!Number.isInteger(n) || n < 0 || n > 255) return undefined;
  if (n < 16) return ANSI_PALETTE[n];
  if (n < 232) {
    const level = (value: number) => (value === 0 ? 0 : 55 + value * 40);
    const index = n - 16;
    return rgb(level(Math.floor(index / 36)), level(Math.floor(index / 6) % 6), level(index % 6));
  }
  const gray = 8 + (n - 232) * 10;
  return rgb(gray, gray, gray);
}

function rgb(red: number, green: number, blue: number): string {
  return `rgb(${red}, ${green}, ${blue})`;
}

/**
 * An extended color, from the codes after 38 or 48: "5;n" (256 colors) or "2;r;g;b" (true color).
 * Returns the color, and how many codes it used.
 */
function extendedColor(codes: number[]): [string | undefined, number] {
  if (codes[0] === 5) return [color256(codes[1]), 2];
  if (codes[0] === 2) {
    const [red, green, blue] = codes.slice(1, 4);
    const valid = [red, green, blue].every((value) => Number.isInteger(value) && value >= 0 && value <= 255);
    return [valid ? rgb(red, green, blue) : undefined, 4];
  }
  return [undefined, 1];
}

/** The style after the given SGR codes. An empty list of codes is a reset. */
export function applySgr(style: AnsiStyle, codes: number[]): AnsiStyle {
  let next: AnsiStyle = { ...style };
  const queue = codes.length === 0 ? [0] : [...codes];
  while (queue.length > 0) {
    const code = queue.shift() as number;
    if (code === 0) next = {};
    else if (code === 1) next.bold = true;
    else if (code === 2) next.dim = true;
    else if (code === 3) next.italic = true;
    else if (code === 4) next.underline = true;
    else if (code === 22) next = { ...next, bold: undefined, dim: undefined };
    else if (code === 23) next.italic = undefined;
    else if (code === 24) next.underline = undefined;
    else if (code >= 30 && code <= 37) next.color = ANSI_PALETTE[code - 30];
    else if (code >= 90 && code <= 97) next.color = ANSI_PALETTE[code - 90 + 8];
    else if (code === 39) next.color = undefined;
    else if (code >= 40 && code <= 47) next.backgroundColor = ANSI_PALETTE[code - 40];
    else if (code >= 100 && code <= 107) next.backgroundColor = ANSI_PALETTE[code - 100 + 8];
    else if (code === 49) next.backgroundColor = undefined;
    else if (code === 38 || code === 48) {
      const [color, used] = extendedColor(queue);
      queue.splice(0, used);
      if (code === 38) next.color = color;
      else next.backgroundColor = color;
    }
  }
  return next;
}

/** The text's segments, each with its style, without the escape sequences. */
export function parseAnsi(text: string): AnsiSegment[] {
  const segments: AnsiSegment[] = [];
  let style: AnsiStyle = {};
  let start = 0;
  const push = (end: number) => {
    if (end > start) segments.push({ text: text.slice(start, end), style });
  };
  for (const match of text.matchAll(ESCAPE_SEQUENCE)) {
    push(match.index);
    start = match.index + match[0].length;
    if (match[2] === "m") {
      const codes = match[1] === "" ? [] : match[1].split(";").map((code) => (code === "" ? 0 : Number(code)));
      style = applySgr(style, codes);
    }
  }
  push(text.length);
  return segments;
}

/** The text without its escape sequences. */
export function stripAnsi(text: string): string {
  return text.replace(ESCAPE_SEQUENCE, "");
}

/** The css of a style. */
export function ansiCss(style: AnsiStyle): CSSProperties {
  const css: CSSProperties = {};
  if (style.color) css.color = style.color;
  if (style.backgroundColor) css.backgroundColor = style.backgroundColor;
  if (style.bold) css.fontWeight = "bold";
  if (style.dim) css.opacity = 0.7;
  if (style.italic) css.fontStyle = "italic";
  if (style.underline) css.textDecoration = "underline";
  return css;
}
