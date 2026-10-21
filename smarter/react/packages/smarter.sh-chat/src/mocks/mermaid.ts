/**
 * A fake mermaid, for tests, because jsdom can't lay out the svg that mermaid renders. Its diagrams
 * are flowcharts whose source starts with "graph", and anything else is invalid. Their svg has the
 * markup that sanitizing must remove: a script, an html foreignObject, and a javascript: link.
 *
 * Tests use it with: vi.mock("mermaid", async () => ({ default: (await import("@/mocks/mermaid")).fakeMermaid }))
 */
import { vi } from "vitest";

export function fakeSvg(id: string): string {
  return (
    `<svg id="${id}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50" aria-roledescription="flowchart-v2">` +
    `<style>#${id} .node rect { fill: #eeeeee; }</style>` +
    `<g class="node"><rect width="80" height="30"></rect><text x="10" y="20">A to B</text></g>` +
    `<script>alert("svg")</script>` +
    `<foreignObject width="10" height="10"><div onclick="alert(1)">html</div></foreignObject>` +
    `<a href="javascript:alert(1)"><text>link</text></a>` +
    `</svg>`
  );
}

export const fakeMermaid = {
  initialize: vi.fn(),
  parse: vi.fn(async (source: string) => (source.trim().startsWith("graph") ? { diagramType: "flowchart-v2" } : false)),
  render: vi.fn(async (id: string) => ({ svg: fakeSvg(id), diagramType: "flowchart-v2" })),
};
