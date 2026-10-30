/** The highlighters' output is markup for the code block's stylesheet, so their tests read the HTML that it renders. */
import { render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CodeBlock, type CodeLine, highlightCss, highlightJson, highlightSql, plainLines } from "./code";

/** Highlighted lines, as HTML, one string per line. */
const html = (lines: CodeLine[]) => lines.map((tokens) => renderToStaticMarkup(<>{tokens}</>));

/** A highlighted span, as HTML. */
const span = (className: string, text: string) => `<span class="${className}">${text}</span>`;

describe("highlightJson", () => {
  it("highlights keys, strings, numbers, literals and punctuation", () => {
    const [line] = html(highlightJson('{ "name": "a", "n": -1.5e3, "ok": true, "none": null }'));
    expect(line).toContain(span("code-key", "&quot;name&quot;"));
    expect(line).toContain(span("code-string", "&quot;a&quot;"));
    expect(line).toContain(span("code-number", "-1.5e3"));
    expect(line).toContain(span("code-literal", "true"));
    expect(line).toContain(span("code-literal", "null"));
    expect(line.startsWith(span("code-punctuation", "{"))).toBe(true);
  });

  it("keeps an escaped quote inside its string, and a line per line", () => {
    const lines = html(highlightJson('{\n  "a": "say \\"hi\\""\n}\n'));
    expect(lines).toHaveLength(3);
    expect(lines[1]).toContain(span("code-string", "&quot;say \\&quot;hi\\&quot;&quot;"));
  });
});

describe("highlightCss", () => {
  it("highlights a rule's selector, and a declaration's property and value", () => {
    const lines = html(highlightCss(':root {\n  app-logo-url: url("https://x/a.png");\n  border-radius: 8px;\n}\n'));
    expect(lines[0]).toBe(`${span("code-selector", ":root")} ${span("code-punctuation", "{")}`);
    expect(lines[1]).toBe(
      `  ${span("code-key", "app-logo-url")}${span("code-punctuation", ":")} ` +
        `${span("code-function", "url")}${span("code-punctuation", "(")}` +
        `${span("code-string", "&quot;https://x/a.png&quot;")}${span("code-punctuation", ")")}` +
        span("code-punctuation", ";"),
    );
    expect(lines[2]).toContain(span("code-number", "8px"));
    expect(lines[3]).toBe(span("code-punctuation", "}"));
  });

  it("highlights colors, functions, keywords and comments, and leaves words plain", () => {
    const [color, rgba, solid, important, comment] = html(
      highlightCss(
        "  color: #231f20;\n  background: rgba(255, 255, 255, 0.88);\n  border: 1px solid;\n" +
          "  color: red !important;\n/* a note */",
      ),
    );
    expect(color).toContain(span("code-number", "#231f20"));
    expect(rgba).toContain(span("code-function", "rgba"));
    expect(rgba).toContain(span("code-number", "0.88"));
    expect(solid).toContain(" solid");
    expect(important).toContain(span("code-keyword", "!important"));
    expect(comment).toBe(span("code-comment", "/* a note */"));
  });
});

describe("highlightSql", () => {
  it("highlights keywords, functions, strings, numbers, parameters and comments", () => {
    const lines = html(
      highlightSql(
        "SELECT\n  COUNT(*) AS n\nFROM\n  users\nWHERE\n  name = {name}\n  AND role = 'admin' -- x\nLIMIT\n  10",
      ),
    );
    expect(lines[0]).toBe(span("code-keyword", "SELECT"));
    expect(lines[1]).toContain(span("code-function", "COUNT"));
    expect(lines[1]).toContain(span("code-keyword", "AS"));
    expect(lines[3]).toBe("  users");
    expect(lines[5]).toContain(span("code-param", "{name}"));
    expect(lines[6]).toContain(span("code-string", "&#x27;admin&#x27;"));
    expect(lines[6]).toContain(span("code-comment", "-- x"));
    expect(lines[8]).toContain(span("code-number", "10"));
  });

  it("highlights true and false as literals, in either case", () => {
    const [line] = html(highlightSql("WHERE a = true OR b = FALSE"));
    expect(line).toContain(span("code-literal", "true"));
    expect(line).toContain(span("code-literal", "FALSE"));
  });
});

describe("plainLines and CodeBlock", () => {
  it("shows code as numbered lines, with a label for a screen reader", () => {
    render(<CodeBlock lines={plainLines("^a+$\nb\n")} label="Pattern" className="extra" />);
    const block = screen.getByLabelText("Pattern");
    expect(block.tagName).toBe("PRE");
    expect(block).toHaveClass("smarter-code-block", "extra");
    // the lines are numbered by the stylesheet, from their class.
    expect(
      renderToStaticMarkup(<CodeBlock lines={plainLines("^a+$\nb\n")} label="Pattern" />).match(/smarter-code-line/g),
    ).toHaveLength(2);
    expect(block).toHaveTextContent("^a+$ b", { normalizeWhitespace: true });
  });
});
