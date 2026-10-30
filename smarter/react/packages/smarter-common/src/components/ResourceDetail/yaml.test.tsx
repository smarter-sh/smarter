/** The highlighter's output is markup for its stylesheet, so its tests read the HTML that it renders. */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { highlightYaml, highlightYamlLine } from "./yaml";

/** A line, highlighted, as HTML. */
const html = (line: string, inBlock = false) => renderToStaticMarkup(<>{highlightYamlLine(line, inBlock)}</>);

/** A highlighted span, as HTML. */
const span = (className: string, text: string) => `<span class="${className}">${text}</span>`;

describe("highlightYamlLine", () => {
  it("highlights a key and its value by its type", () => {
    expect(html("  name: pii_redaction")).toBe(
      `  ${span("yaml-key", "name")}${span("yaml-punctuation", ":")} ${span("yaml-string", "pii_redaction")}`,
    );
    expect(html("threshold: 0.85")).toContain(span("yaml-number", "0.85"));
    expect(html("enabled: true")).toContain(span("yaml-literal", "true"));
    expect(html("replacement: null")).toContain(span("yaml-literal", "null"));
    expect(html("prompt: |")).toContain(span("yaml-punctuation", "|"));
  });

  it("highlights a list item, a comment, and a comment after a value", () => {
    expect(html("  - red")).toBe(`  ${span("yaml-punctuation", "- ")}${span("yaml-string", "red")}`);
    expect(html("  # a comment")).toBe(span("yaml-comment", "  # a comment"));
    expect(html("name: x # why")).toContain(span("yaml-comment", " # why"));
    // a # inside a quoted string is not a comment.
    expect(html("description: 'a # b'")).toContain(span("yaml-string", "&#x27;a # b&#x27;"));
  });

  it("leaves a key without a value, and a line of a block scalar", () => {
    expect(html("metadata:")).toBe(`${span("yaml-key", "metadata")}${span("yaml-punctuation", ":")}`);
    expect(html("    key: text", true)).toBe(span("yaml-string", "    key: text"));
  });
});

describe("highlightYaml", () => {
  it("highlights a block scalar's lines as a string, until the indentation ends", () => {
    const lines = highlightYaml("prompt: |\n  key: text\n\n  more\nnext: 1\n").map((tokens) =>
      renderToStaticMarkup(<>{tokens}</>),
    );
    expect(lines).toHaveLength(5);
    expect(lines[1]).toBe(span("yaml-string", "  key: text"));
    expect(lines[3]).toBe(span("yaml-string", "  more"));
    expect(lines[4]).toContain(span("yaml-key", "next"));
  });
});
