import { afterEach, describe, expect, it, vi } from "vitest";

import { mathHtml } from "./math";
import { convertMarkdownToHTML } from "./messages";

/** The message's html, as a document fragment, to query as the browser would display it. */
function typeset(markdown: string): HTMLElement {
  const element = document.createElement("div");
  element.innerHTML = convertMarkdownToHTML(markdown);
  return element;
}

/** The LaTeX source of each typeset expression, from KaTeX's MathML annotation. */
function sources(element: HTMLElement): string[] {
  return [...element.querySelectorAll(".katex annotation")].map((annotation) => annotation.textContent ?? "");
}

describe("mathHtml", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("typesets inline and display math", () => {
    expect(mathHtml("x^2", false)).toContain('<span class="katex">');
    expect(mathHtml("x^2", false)).not.toContain("katex-display");
    expect(mathHtml("x^2", true)).toContain('<span class="katex-display">');
  });

  it("displays invalid LaTeX as its source, rather than throwing", () => {
    const html = mathHtml(String.raw`\frac{1}{`, false);
    expect(html).toContain("katex-error");
    expect(html).toContain(String.raw`\frac{1}{`);
  });

  it("displays a dollar sign in math, e.g. a price, as a dollar sign", () => {
    for (const tex of ["$1.20", String.raw`\$1.20`]) {
      const html = mathHtml(tex, false);
      expect(html).not.toContain("katex-error");
      expect(html).toContain("$");
    }
  });

  it("does not warn about unicode in math", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    mathHtml("3 × 4 = 12", false);
    expect(warn).not.toHaveBeenCalled();
  });

  it("does not let math link or add markup", () => {
    const element = document.createElement("div");
    element.innerHTML = mathHtml(String.raw`\href{javascript:alert(1)}{x} \htmlClass{evil}{y}`, false);
    expect(element.querySelector("a, [href], .evil")).toBeNull();
  });
});

describe("convertMarkdownToHTML, with math", () => {
  it("typesets \\(...\\) inline, within its paragraph", () => {
    const element = typeset(String.raw`Each term is \(F_n = F_{n-1} + F_{n-2}\), for \(n > 1\).`);
    expect(sources(element)).toEqual(["F_n = F_{n-1} + F_{n-2}", "n > 1"]);
    expect(element.querySelector(".katex-display")).toBeNull();
    expect(element).toHaveTextContent("Each term is");
    expect(element).not.toHaveTextContent("\\(");
  });

  it("displays \\[...\\] and $$...$$ on lines of their own", () => {
    const element = typeset(
      "The ratio:\n\n\\[\n\\varphi = \\frac{1 + \\sqrt{5}}{2}\n\\]\n\nand\n\n$$\nE = mc^2\n$$\n\nDone.",
    );
    expect(sources(element)).toEqual([String.raw`\varphi = \frac{1 + \sqrt{5}}{2}`, "E = mc^2"]);
    expect(element.querySelectorAll(".katex-display")).toHaveLength(2);
    expect(element).toHaveTextContent("Done.");
  });

  it("keeps a display equation whole, rather than reading its lines as markdown", () => {
    const element = typeset("$$\na\n+ b\n- c\n= d\n$$");
    expect(sources(element)).toEqual(["a\n+ b\n- c\n= d"]);
    expect(element.querySelector("ul, h1, h2")).toBeNull();
  });

  it("displays an equation that follows a line of text, without a blank line between them", () => {
    // the line of "=" would otherwise make the text and the equation's first side a setext heading.
    const equation = "\\[\nx^2 + \\frac{b}{a}x\n=\n-\\frac{c}{a}\n\\]";
    for (const markdown of [
      `Add the square to both sides:\n${equation}\n\nNext.`,
      `1. Add the square to both sides:\n${equation}\n2. Next.`,
      "Subtract:\n$$\na\n-\nb\n$$",
    ]) {
      const element = typeset(markdown);
      expect(element.querySelectorAll(".katex-display")).toHaveLength(1);
      expect(element.querySelector("h1, h2")).toBeNull();
      expect(element).toHaveTextContent(/^(Add the square to both sides:|Subtract:)/);
    }
  });

  it("keeps setext headings without math", () => {
    const element = typeset("Quadratics\n==========\n\nAnd more\n---\n\ntext");
    expect(element.querySelector("h1")).toHaveTextContent("Quadratics");
    expect(element.querySelector("h2")).toHaveTextContent("And more");
  });

  it("displays \\[...\\] and $$...$$ within a line of text", () => {
    const element = typeset(String.raw`So \[a^2 + b^2 = c^2\] and $$x = 1$$ hold.`);
    expect(sources(element)).toEqual(["a^2 + b^2 = c^2", "x = 1"]);
    expect(element.querySelectorAll(".katex-display")).toHaveLength(2);
  });

  it("typesets math in lists, tables and block quotes", () => {
    const element = typeset("- \\(a\\)\n\n| x | y |\n| - | - |\n| \\(b\\) | 1 |\n\n> \\(c\\)");
    expect(sources(element)).toEqual(["a", "b", "c"]);
    expect(element.querySelector("li .katex, td .katex, blockquote .katex")).not.toBeNull();
  });

  it("does not read single dollar signs, e.g. prices, as math", () => {
    const element = typeset("It costs $5, or $10 with shipping.");
    expect(element.querySelector(".katex")).toBeNull();
    expect(element).toHaveTextContent("It costs $5, or $10 with shipping.");
  });

  it("keeps math in code spans and code blocks as code", () => {
    const element = typeset("Write `\\(x\\)` for inline math.\n\n```latex\n$$\nx\n$$\n```");
    expect(element.querySelector(".katex")).toBeNull();
    expect(element.querySelector("p code")).toHaveTextContent("\\(x\\)");
    expect(element.querySelector("pre code")).toHaveTextContent("$$ x $$");
  });

  it("displays unfinished math, e.g. while a response is streaming, as text", () => {
    const element = typeset("The ratio is \\[ \\varphi = \\frac{1");
    expect(element.querySelector(".katex")).toBeNull();
    expect(element).toHaveTextContent("\\varphi");
  });

  it("keeps KaTeX's html and MathML through sanitizing", () => {
    const element = typeset(String.raw`\(\sqrt{2}\)`);
    expect(element.querySelector(".katex .katex-html")).not.toBeNull();
    expect(element.querySelector(".katex math semantics annotation")).not.toBeNull();
    expect(element.querySelector(".katex-html .sqrt svg path")).not.toBeNull();
    expect(element.querySelector(".katex-html [style]")).not.toBeNull();
  });

  it("does not let math inject markup", () => {
    const element = typeset(String.raw`\(\text{<img src=x onerror=alert(1)>}\)`);
    expect(element.querySelector("img")).toBeNull();
    expect(element.querySelector("[onerror]")).toBeNull();
  });
});
