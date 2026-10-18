import { describe, expect, it } from "vitest";

import { bracketDepthChange, hasJsonBlock, logLines, logNodes, type LogNode } from "./logJson";

const text = (segments: { text: string }[]) => segments.map((segment) => segment.text).join("");

/** The nodes, as plain text: lines as strings, blocks as [open, children, close, lines]. */
function outline(nodes: LogNode[]): unknown[] {
  return nodes.map((node) =>
    node.kind === "line"
      ? text(node.segments)
      : [text(node.open), outline(node.children), text(node.close), node.lines],
  );
}

describe("bracketDepthChange", () => {
  it("counts the brackets outside strings", () => {
    expect(bracketDepthChange('request: {"a": [')).toBe(2);
    expect(bracketDepthChange("  ]},")).toBe(-2);
    expect(bracketDepthChange('"not {a} [block]"')).toBe(0);
    expect(bracketDepthChange('"escaped \\" quote {"')).toBe(0);
    expect(bracketDepthChange('{"a": "\\\\"}')).toBe(0);
  });
});

describe("logLines", () => {
  it("splits the record into lines, and keeps a color that spans lines", () => {
    const lines = logLines('\u001b[32m{\n  "a": 1\n}\u001b[0m done');
    expect(lines.map(text)).toEqual(["{", '  "a": 1', "} done"]);
    expect(lines[1][0].style.color).toBeDefined();
    expect(lines[2][1].style.color).toBeUndefined();
  });
});

describe("logNodes", () => {
  it("groups pretty-printed JSON into blocks, nested ones too", () => {
    const message = [
      "chat_response request: {",
      '  "model": "gpt",',
      '  "messages": [',
      '    {"role": "user", "content": "a } in a string"}',
      "  ]",
      "}, ",
      "response: {",
      '  "id": "x"',
      "}",
    ].join("\n");
    const nodes = logNodes(message);
    expect(hasJsonBlock(nodes)).toBe(true);
    expect(outline(nodes)).toEqual([
      [
        "chat_response request: {",
        ['  "model": "gpt",', ['  "messages": [', ['    {"role": "user", "content": "a } in a string"}'], "  ]", 1]],
        "}, ",
        4,
      ],
      ["response: {", ['  "id": "x"'], "}", 1],
    ]);
  });

  it("leaves a record without multi-line JSON as lines", () => {
    for (const message of ["one line", 'data: {"a": 1}', "{\n}", 'cut short: {\n  "a": 1']) {
      expect(hasJsonBlock(logNodes(message))).toBe(false);
    }
  });
});
