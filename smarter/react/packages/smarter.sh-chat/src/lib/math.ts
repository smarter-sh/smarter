/**
 * Math in markdown messages, written in LaTeX and typeset by KaTeX, as GitHub and ChatGPT display it.
 *
 * The delimiters are the ones that LLMs write: ``\(...\)`` for inline math, and ``\[...\]`` or
 * ``$$...$$`` for display math, which is centered on a line of its own. Single dollar signs are not
 * math, so that prices, e.g. "$5 or $10", stay as text.
 *
 * The delimiters are tokenized before markdown's own rules, which would otherwise turn ``\(`` into
 * "(", and the lines of a display equation into lists or headings. Math in code spans and code blocks
 * stays as code. KaTeX runs synchronously, as the markdown renderer does. Invalid LaTeX, e.g. a
 * response that is still streaming, is displayed as its source rather than throwing. KaTeX's css and
 * fonts are imported here. See math.css.
 */
import katex from "katex";
import "katex/dist/katex.min.css";
import type { MarkedExtension, Tokens } from "marked";

import "./math.css";

interface MathToken extends Tokens.Generic {
  type: "blockMath" | "inlineMath";
  raw: string;
  text: string;
  displayMode: boolean;
}

// a display equation on lines of its own: $$...$$ or \[...\], indented by up to three spaces.
const BLOCK_MATH_REGEX = /^ {0,3}(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])[ \t]*(?:\n+|$)/;
const BLOCK_MATH_START_REGEX = /^ {0,3}(?:\$\$|\\\[)/m;
// math within a line of text: \(...\) inline, and $$...$$ or \[...\] displayed.
const INLINE_MATH_REGEX = /^(?:\\\(([\s\S]+?)\\\)|\\\[([\s\S]+?)\\\]|\$\$([\s\S]+?)\$\$)/;
const INLINE_MATH_START_REGEX = /\\\(|\\\[|\$\$/;

/**
 * Html for a LaTeX expression, inline or displayed, or for its source if it is not valid LaTeX. A
 * dollar sign, which is not valid in math, e.g. a price in \($1.20\), is a dollar sign.
 */
export function mathHtml(tex: string, displayMode: boolean): string {
  return katex.renderToString(tex.trim().replace(/(?<!\\)\$/g, "\\$"), {
    displayMode,
    throwOnError: false,
    // LLMs write unicode, e.g. "×", in math. KaTeX displays it, and need not warn in the console.
    strict: "ignore",
    // no \href, \url, \includegraphics or \htmlClass: math is text, and cannot link or add markup.
    trust: false,
  });
}

function mathToken(type: MathToken["type"], raw: string, text: string, displayMode: boolean): MathToken {
  return { type, raw, text, displayMode };
}

/**
 * The marked extension that tokenizes and renders math. See convertMarkdownToHTML in messages.ts.
 *
 * A display equation that follows a line of text, without a blank line between them, would be read
 * as part of that paragraph, and a line of its own that is "=" or "-", e.g. between the two sides of
 * an equation, would make the paragraph a setext heading, which splits the equation. So a setext
 * heading that contains a display equation is not a heading: the paragraph then ends where the
 * equation begins, and blockMath tokenizes it.
 */
export const mathExtension: MarkedExtension = {
  tokenizer: {
    lheading(src: string) {
      const heading = /^(?:[^\n]+\n)+?(?: {0,3}(?:=+|-+) *(?:\n+|$))/.exec(src)?.[0] ?? "";
      // undefined: not a heading. false: marked's own lheading tokenizer decides.
      return BLOCK_MATH_START_REGEX.test(heading) ? undefined : false;
    },
  },
  extensions: [
    {
      name: "blockMath",
      level: "block",
      start: (src: string) => src.match(BLOCK_MATH_START_REGEX)?.index,
      tokenizer(src: string): MathToken | undefined {
        const match = BLOCK_MATH_REGEX.exec(src);
        if (!match) return undefined;
        return mathToken("blockMath", match[0], match[1] ?? match[2], true);
      },
      renderer: (token: Tokens.Generic) => `${mathHtml(token.text, true)}\n`,
    },
    {
      name: "inlineMath",
      level: "inline",
      start: (src: string) => src.match(INLINE_MATH_START_REGEX)?.index,
      tokenizer(src: string): MathToken | undefined {
        const match = INLINE_MATH_REGEX.exec(src);
        if (!match) return undefined;
        const [raw, inline, bracketed, dollars] = match;
        return mathToken("inlineMath", raw, inline ?? bracketed ?? dollars, inline === undefined);
      },
      renderer: (token: Tokens.Generic) => mathHtml(token.text, token.displayMode),
    },
  ],
};
