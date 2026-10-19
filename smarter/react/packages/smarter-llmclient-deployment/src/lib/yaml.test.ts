import { describe, expect, it } from "vitest";

import { highlightYaml, type YamlToken } from "@/lib/yaml";

/** A line's tokens, as "kind:text" strings. */
const kinds = (tokens: YamlToken[]) => tokens.map(({ kind, text }) => `${kind}:${text}`);

describe("highlightYaml", () => {
  it("colors keys, strings, literals and list items", () => {
    const lines = highlightYaml("kind: LLMClient\ncount: 3\nok: true\nitems:\n  - one\n  - name: two\n# note");
    expect(kinds(lines[0])).toEqual(["key:kind", "punctuation::", "plain: ", "string:LLMClient"]);
    expect(kinds(lines[1])).toEqual(["key:count", "punctuation::", "plain: ", "literal:3"]);
    expect(kinds(lines[2])).toEqual(["key:ok", "punctuation::", "plain: ", "literal:true"]);
    expect(kinds(lines[3])).toEqual(["key:items", "punctuation::"]);
    expect(kinds(lines[4])).toEqual(["plain:  ", "punctuation:- ", "string:one"]);
    expect(kinds(lines[5])).toEqual([
      "plain:  ",
      "punctuation:- ",
      "key:name",
      "punctuation::",
      "plain: ",
      "string:two",
    ]);
    expect(kinds(lines[6])).toEqual(["plain:# note"]);
  });

  it("colors a literal block's lines, and its blank lines, as strings", () => {
    const lines = highlightYaml("role: |\n  line one\n\n  line two\nnext: x");
    expect(kinds(lines[0])).toEqual(["key:role", "punctuation::", "plain: ", "block:|"]);
    expect(kinds(lines[1])).toEqual(["string:  line one"]);
    expect(kinds(lines[2])).toEqual(["string:"]);
    expect(kinds(lines[3])).toEqual(["string:  line two"]);
    expect(kinds(lines[4])[0]).toBe("key:next");
  });

  it("ends a list item's literal block at the item's own keys", () => {
    const lines = highlightYaml("- name: a\n  text: >\n    folded\n  next: b");
    expect(kinds(lines[2])).toEqual(["string:    folded"]);
    expect(kinds(lines[3])).toContain("key:next");
  });

  it("keeps the text exactly, html and all", () => {
    const text = "a: <script>x</script>\n- <b>\n  <i>: |\n    <u>\n<p>\nkey:   ";
    expect(
      highlightYaml(text)
        .map((tokens) => tokens.map((token) => token.text).join(""))
        .join("\n"),
    ).toBe(text);
  });
});
