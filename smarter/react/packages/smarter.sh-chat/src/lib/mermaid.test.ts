import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeMermaid } from "@/mocks/mermaid";

import { escapeQuotedLabels, renderMermaidDiagrams, sanitizeSvg, toggleMermaidDiagram } from "./mermaid";
import { convertMarkdownToHTML } from "./messages";

vi.mock("mermaid", async () => ({ default: (await import("@/mocks/mermaid")).fakeMermaid }));

/** A message, in the page, with the given markdown. */
function message(markdown: string): HTMLElement {
  const element = document.createElement("div");
  element.innerHTML = convertMarkdownToHTML(markdown);
  document.body.append(element);
  return element;
}

/** A mermaid code block. Each test uses its own source, because diagrams are cached by source. */
function diagram(name: string): string {
  return `\`\`\`mermaid\ngraph TD\n  ${name}A --> ${name}B\n\`\`\``;
}

function code(element: HTMLElement): HTMLElement {
  return element.querySelector("pre") as HTMLElement;
}

function figure(element: HTMLElement): HTMLElement | null {
  return element.querySelector('[role="figure"]');
}

function toggle(element: HTMLElement): HTMLButtonElement | null {
  return element.querySelector("button.smarter-chat-mermaid-toggle");
}

describe("renderMermaidDiagrams", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("displays a mermaid code block as its diagram, with a button that shows its code", async () => {
    const element = message(`Here it is:\n\n${diagram("display")}`);
    await renderMermaidDiagrams(element);

    expect(figure(element)).toHaveAccessibleName("Diagram");
    expect(figure(element)?.querySelector("svg")).not.toBeNull();
    expect(code(element)).not.toBeVisible();
    expect(toggle(element)).toHaveAccessibleName("Show the diagram's code");
    // the toggle is beside the copy button, which still copies the code.
    expect(toggle(element)?.nextElementSibling).toHaveAccessibleName("Copy code");
    expect(fakeMermaid.initialize).toHaveBeenCalledWith(
      expect.objectContaining({
        startOnLoad: false,
        securityLevel: "strict",
        htmlLabels: false,
        themeVariables: expect.objectContaining({ pie1: "#2563eb" }),
      }),
    );
  });

  it("sanitizes the diagram's svg, but keeps its styles", async () => {
    const element = message(diagram("sanitize"));
    await renderMermaidDiagrams(element);
    const svg = figure(element)?.querySelector("svg");

    expect(svg?.querySelector("style")).toHaveTextContent(".node rect");
    expect(svg?.querySelector("rect")).not.toBeNull();
    expect(svg?.querySelector("script, foreignObject, [onclick], [href^='javascript']")).toBeNull();
  });

  it("leaves a diagram that mermaid can't parse, or can't render, as its code block", async () => {
    const element = message("```mermaid\nnot a diagram\n```");
    await renderMermaidDiagrams(element);
    expect(fakeMermaid.render).not.toHaveBeenCalled();

    fakeMermaid.render.mockRejectedValueOnce(new Error("no layout"));
    const failed = message(diagram("render-error"));
    await renderMermaidDiagrams(failed);

    for (const element_ of [element, failed]) {
      expect(figure(element_)).toBeNull();
      expect(toggle(element_)).toBeNull();
      expect(code(element_)).toBeVisible();
    }
  });

  it("leaves other code blocks as they are", async () => {
    const element = message("```python\nprint('graph TD')\n```");
    await renderMermaidDiagrams(element);
    expect(figure(element)).toBeNull();
    expect(fakeMermaid.parse).not.toHaveBeenCalled();
  });

  it("renders each diagram once, and displays it again from the cache", async () => {
    const first = message(diagram("cache"));
    await renderMermaidDiagrams(first);
    await renderMermaidDiagrams(first);
    const again = message(diagram("cache"));
    await renderMermaidDiagrams(again);

    expect(fakeMermaid.render).toHaveBeenCalledTimes(1);
    expect(first.querySelectorAll('[role="figure"]')).toHaveLength(1);
    expect(figure(again)).not.toBeNull();
  });

  it("skips a block that leaves the page while its diagram renders, until it returns", async () => {
    const element = message(diagram("detached"));
    // renderMermaidDiagrams is not testing-library's render, whose result the rule names.
    // eslint-disable-next-line testing-library/render-result-naming-convention
    const pending = renderMermaidDiagrams(element);
    element.remove();
    await pending;
    expect(figure(element)).toBeNull();

    document.body.append(element);
    await renderMermaidDiagrams(element);
    expect(figure(element)).not.toBeNull();
  });

  it("does nothing without a root", async () => {
    await expect(renderMermaidDiagrams(null)).resolves.toBeUndefined();
  });
});

describe("renderMermaidDiagrams, when mermaid can't be loaded", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("leaves the code block, and tries again for the next diagram", async () => {
    // a fresh module, so that mermaid has not been loaded yet.
    vi.resetModules();
    const { renderMermaidDiagrams: render } = await import("./mermaid");
    fakeMermaid.initialize.mockImplementationOnce(() => {
      throw new Error("chunk failed to load");
    });

    const element = message(diagram("load-error"));
    await render(element);
    expect(figure(element)).toBeNull();
    expect(code(element)).toBeVisible();

    const retried = message(diagram("load-error"));
    await render(retried);
    expect(figure(retried)).not.toBeNull();
  });
});

describe("toggleMermaidDiagram", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("shows the diagram's code, and the diagram again", async () => {
    const element = message(diagram("toggle"));
    await renderMermaidDiagrams(element);
    const button = toggle(element) as HTMLButtonElement;

    expect(toggleMermaidDiagram(button)).toBe(true);
    expect(code(element)).toBeVisible();
    expect(figure(element)).not.toBeVisible();
    expect(button).toHaveTextContent("Diagram");
    expect(button).toHaveAccessibleName("Show the diagram");

    expect(toggleMermaidDiagram(button)).toBe(true);
    expect(code(element)).not.toBeVisible();
    expect(figure(element)).toBeVisible();
    expect(button).toHaveTextContent("Code");
  });

  it("ignores clicks on anything else", async () => {
    const element = message(`text\n\n${diagram("ignore")}`);
    await renderMermaidDiagrams(element);
    expect(toggleMermaidDiagram(element.querySelector("p"))).toBe(false);
    expect(toggleMermaidDiagram(null)).toBe(false);
    expect(code(element)).not.toBeVisible();
  });
});

describe("escapeQuotedLabels", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.clearAllMocks();
  });

  it("writes the > of quoted labels as #gt;, which mermaid would otherwise drop", () => {
    expect(escapeQuotedLabels('A["a >= b > 0"] -->|"x > 1"| B')).toBe('A["a #gt;= b #gt; 0"] -->|"x #gt; 1"| B');
  });

  it("leaves arrows, and labels without quotes, as they are", () => {
    expect(escapeQuotedLabels("A[x > 1] --> B\nAlice->>Bob: y > 2")).toBe("A[x > 1] --> B\nAlice->>Bob: y > 2");
  });

  it("is what mermaid renders, while the cache keeps the source", async () => {
    const element = message('```mermaid\ngraph TD\n  A["n > 0"] --> B\n```');
    await renderMermaidDiagrams(element);
    expect(fakeMermaid.render).toHaveBeenCalledWith(expect.any(String), 'graph TD\n  A["n #gt; 0"] --> B');
  });
});

describe("sanitizeSvg", () => {
  it("removes scripts and event handlers, and keeps svg and its styles", () => {
    const svg = sanitizeSvg(
      '<svg xmlns="http://www.w3.org/2000/svg"><style>.a { fill: red; }</style><circle class="a" r="1" onload="alert(1)"></circle><script>alert(1)</script></svg>',
    );
    expect(svg).toContain("<style>.a { fill: red; }</style>");
    expect(svg).toContain('<circle class="a" r="1"></circle>');
    expect(svg).not.toContain("onload");
    expect(svg).not.toContain("<script");
  });
});
