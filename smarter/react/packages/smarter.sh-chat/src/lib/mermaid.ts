/**
 * Mermaid diagrams in markdown messages: a ```mermaid code block is displayed as its diagram, with a
 * button in its header that shows its code instead, and back.
 *
 * Mermaid renders asynchronously, but markdown is rendered to an html string synchronously (see
 * messages.ts). So a mermaid block is rendered as a code block, like any other (see code.ts), and
 * renderMermaidDiagrams() then replaces it, in the page, with its diagram. SmarterChat calls it
 * whenever its messages change. Diagrams are cached by their source, so that a message that is
 * displayed again, e.g. when the backend's messages are shown or hidden, is not rendered again.
 *
 * Mermaid is large, so it is imported only when a message first has a diagram (see mermaidImport.ts,
 * which the embed script replaces with its own). A diagram that
 * mermaid cannot render, e.g. because the LLM wrote invalid syntax, stays as its code block.
 *
 * Mermaid runs with its "strict" security level, and with svg text labels rather than html ones,
 * and its svg is sanitized again before it is displayed, because the diagram's source comes from
 * the LLM. The buttons work by event delegation, as the copy button does. See toggleMermaidDiagram,
 * and SmarterChat's onClick.
 */
import DOMPurify from "dompurify";

import { CODE_BLOCK_CLASS, COPY_BUTTON_CLASS, MERMAID_BLOCK_CLASS } from "./code";
import { gettext, pgettext } from "./i18n";
import { importMermaid } from "./mermaidImport";
import "./mermaid.css";

export const DIAGRAM_CLASS = "smarter-chat-mermaid-diagram";
export const TOGGLE_BUTTON_CLASS = "smarter-chat-mermaid-toggle";

interface ToggleLabels {
  label: string;
  name: string;
}

/** The text and the accessible name of the button that shows a diagram's code. */
function showCodeLabels(): ToggleLabels {
  // Translators: a button that shows the code of a diagram, instead of the diagram.
  return { label: pgettext("button", "Code"), name: gettext("Show the diagram's code") };
}

/** The text and the accessible name of the button that shows a diagram again, instead of its code. */
function showDiagramLabels(): ToggleLabels {
  // Translators: a button that shows a diagram, instead of its code.
  return { label: pgettext("button", "Diagram"), name: gettext("Show the diagram") };
}

type Mermaid = Awaited<ReturnType<typeof importMermaid>>["default"];

// distinct, saturated colors for the lines and bars of charts, and the slices of pie charts. The
// neutral theme's own are shades of gray, and its xychart lines are almost invisible.
const PALETTE = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d"];
const THEME_VARIABLES = {
  xyChart: { plotColorPalette: PALETTE.join(", ") },
  ...Object.fromEntries(PALETTE.map((color, index) => [`pie${index + 1}`, color])),
};

let mermaidPromise: Promise<Mermaid> | null = null;
let diagramCount = 0;
// the svg of each diagram, by its source, or null if mermaid cannot render it.
const diagrams = new Map<string, Promise<string | null>>();

/** Mermaid, imported and initialized the first time that it is needed. */
function loadMermaid(): Promise<Mermaid> {
  mermaidPromise ??= importMermaid()
    .then(({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        htmlLabels: false,
        theme: "neutral",
        themeVariables: THEME_VARIABLES,
      });
      return mermaid;
    })
    .catch((error: unknown) => {
      // e.g. a network error while loading its chunk. The next diagram tries again.
      mermaidPromise = null;
      throw error;
    });
  return mermaidPromise;
}

/** A diagram's svg, without anything that could run a script, but with its own styles. */
export function sanitizeSvg(svg: string): string {
  return DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true }, ADD_TAGS: ["style"] });
}

/**
 * A diagram's source, with the ">" of its quoted labels written as mermaid's "#gt;". With svg text
 * labels, mermaid drops ">" from quoted flowchart labels, e.g. "a >= b > 0" is drawn as "a = b 0".
 * Other diagrams display "#gt;" as ">" too.
 */
export function escapeQuotedLabels(source: string): string {
  return source.replace(/"[^"\n]*"/g, (label) => label.replace(/>/g, "#gt;"));
}

/** A diagram's sanitized svg, or null if its syntax is invalid. Throws if mermaid can't be loaded. */
async function renderDiagram(source: string): Promise<string | null> {
  const mermaid = await loadMermaid();
  const escaped = escapeQuotedLabels(source);
  try {
    if (!(await mermaid.parse(escaped, { suppressErrors: true }))) return null;
    diagramCount += 1;
    const { svg } = await mermaid.render(`smarter-chat-mermaid-${diagramCount}`, escaped);
    return sanitizeSvg(svg);
  } catch {
    return null;
  }
}

/** A diagram's sanitized svg, rendered once for each source, or null if it can't be rendered. */
export function diagramSvg(source: string): Promise<string | null> {
  let svg = diagrams.get(source);
  if (!svg) {
    svg = renderDiagram(source).catch(() => {
      // mermaid could not be loaded. Don't cache that, so that the diagram can be tried again.
      diagrams.delete(source);
      return null;
    });
    diagrams.set(source, svg);
  }
  return svg;
}

/** Displays a mermaid code block as its diagram, and adds the button that shows its code. */
function showDiagram(block: HTMLElement, svg: string): void {
  const pre = block.querySelector("pre");
  const copy = block.querySelector(`.${CODE_BLOCK_CLASS}-header .${COPY_BUTTON_CLASS}`);
  if (!pre || !copy) return;
  const diagram = document.createElement("div");
  diagram.className = DIAGRAM_CLASS;
  // a figure, rather than an img, so that mermaid's own accessible title and description are kept.
  diagram.setAttribute("role", "figure");
  diagram.setAttribute("aria-label", gettext("Diagram"));
  diagram.innerHTML = svg;
  pre.before(diagram);
  pre.hidden = true;
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = TOGGLE_BUTTON_CLASS;
  const labels = showCodeLabels();
  toggle.textContent = labels.label;
  toggle.setAttribute("aria-label", labels.name);
  copy.before(toggle);
}

/**
 * Displays the mermaid code blocks within root as their diagrams. Blocks that are already
 * displayed, or are being rendered, are left as they are. A block that leaves the page while its
 * diagram renders, e.g. because its message was displayed again, is skipped: its new block finds
 * the diagram in the cache.
 */
export async function renderMermaidDiagrams(root: ParentNode | null | undefined): Promise<void> {
  if (!root) return;
  const blocks = [...root.querySelectorAll<HTMLElement>(`.${MERMAID_BLOCK_CLASS}:not([data-diagram])`)];
  await Promise.all(
    blocks.map(async (block) => {
      block.dataset.diagram = "pending";
      const source = (block.querySelector("pre code")?.textContent ?? "").replace(/\n$/, "");
      const svg = await diagramSvg(source);
      if (!block.isConnected) {
        delete block.dataset.diagram;
        return;
      }
      if (svg) showDiagram(block, svg);
      block.dataset.diagram = svg ? "rendered" : "failed";
    }),
  );
}

/**
 * Shows a diagram's code instead of the diagram, or the diagram again, when its button is clicked.
 * Clicks on anything else are ignored.
 *
 * :returns: whether the click was on a diagram's button.
 */
export function toggleMermaidDiagram(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  const button = target.closest<HTMLButtonElement>(`button.${TOGGLE_BUTTON_CLASS}`);
  const block = button?.closest(`.${MERMAID_BLOCK_CLASS}`);
  const diagram = block?.querySelector<HTMLElement>(`.${DIAGRAM_CLASS}`);
  const pre = block?.querySelector("pre");
  if (!button || !diagram || !pre) return false;
  const showCode = pre.hidden;
  pre.hidden = !showCode;
  diagram.hidden = showCode;
  const next = showCode ? showDiagramLabels() : showCodeLabels();

  button.textContent = next.label;
  button.setAttribute("aria-label", next.name);
  return true;
}
