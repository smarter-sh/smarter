import fs from "node:fs";
import { describe, expect, it } from "vitest";

import {
  ExtractionError,
  MESSAGES_FILE,
  extractFromSource,
  extractMessages,
  formatMessages,
  sourceFiles,
} from "./extract";

describe("extractFromSource", () => {
  it("extracts each kind of call", () => {
    const source = `
      const a = gettext("Secrets");
      const b = ngettext("%(count)s secret", "%(count)s secrets", n);
      const c = pgettext("verb", "Clone");
      const d = npgettext("list", "one row", "%(count)s rows", n);
    `;
    expect(extractFromSource("App.tsx", source)).toEqual([
      { singular: "Secrets", files: ["App.tsx"], comments: [] },
      { singular: "%(count)s secret", plural: "%(count)s secrets", files: ["App.tsx"], comments: [] },
      { context: "verb", singular: "Clone", files: ["App.tsx"], comments: [] },
      { context: "list", singular: "one row", plural: "%(count)s rows", files: ["App.tsx"], comments: [] },
    ]);
  });

  it("extracts plain JavaScript", () => {
    expect(extractFromSource("sign-in.js", 'Swal.fire({ text: gettext("Ok, got it!") });')).toEqual([
      { singular: "Ok, got it!", files: ["sign-in.js"], comments: [] },
    ]);
  });

  it("extracts calls in JSX, template literals and concatenations", () => {
    const source = `
      const App = () => (
        <p title={gettext(\`Title\`)}>{gettext("Long " + "message")}</p>
      );
    `;
    expect(extractFromSource("App.tsx", source).map((m) => m.singular)).toEqual(["Title", "Long message"]);
  });

  it("ignores other functions, and methods named gettext", () => {
    const source = `window.django.gettext(msgid); translate("x"); obj.gettext("y");`;
    expect(extractFromSource("i18n.tsx", source)).toEqual([]);
  });

  it("keeps the translator comments on the line before, or earlier on the same line", () => {
    const source = `
      // Translators: the title of the secrets page
      const a = gettext("Secrets");
      const b = /* Translators: a verb */ gettext("Clone");
      const c = (
        <p>
          {/* Translators: a noun */}
          {gettext("Clone")}
        </p>
      );
      // an unrelated comment
      const d = gettext("Rename");
    `;
    const messages = extractFromSource("App.tsx", source);
    expect(messages.map((m) => m.comments)).toEqual([
      ["Translators: the title of the secrets page"],
      ["Translators: a verb"],
      ["Translators: a noun"],
      [],
    ]);
  });

  it("refuses a message that isn't a string literal", () => {
    expect(() => extractFromSource("App.tsx", "gettext(message);")).toThrow(ExtractionError);
    expect(() => extractFromSource("App.tsx", "gettext(`Hello ${name}`);")).toThrow(/App.tsx:1:1: argument 1/);
    expect(() => extractFromSource("App.tsx", 'ngettext("one", plural, n);')).toThrow(/argument 2 of ngettext/);
    expect(() => extractFromSource("App.tsx", "gettext();")).toThrow(ExtractionError);
  });

  it("refuses an HTML entity in a React message, but not in static/js", () => {
    expect(() => extractFromSource("App.tsx", 'gettext("Build one &rarr;");')).toThrow(
      /must not contain an HTML entity/,
    );
    expect(() => extractFromSource("App.tsx", 'gettext("Copyright &#169;");')).toThrow(ExtractionError);
    expect(() => extractFromSource("App.tsx", 'ngettext("one", "two &middot; three", n);')).toThrow(/argument 2/);
    expect(extractFromSource("App.tsx", 'gettext("Build one →");')[0].singular).toBe("Build one →");
    expect(extractFromSource("App.tsx", 'gettext("Salt & pepper; to taste");')[0].singular).toBe(
      "Salt & pepper; to taste",
    );
    expect(extractFromSource("static.js", 'gettext("Build one &rarr;");')[0].singular).toBe("Build one &rarr;");
  });
});

describe("formatMessages", () => {
  it("writes one call per message, after its comments", () => {
    const js = formatMessages([
      { singular: 'Say "hi"', files: ["a.tsx", "b.tsx"], comments: ["Translators: a greeting"] },
      { singular: "one", plural: "many", files: ["a.tsx"], comments: [] },
      { context: "verb", singular: "Clone", files: ["a.tsx"], comments: [] },
      { context: "list", singular: "one", plural: "many", files: ["a.tsx"], comments: [] },
    ]);
    expect(js).toContain(
      '// Translators: a greeting\n// Translators: used in a.tsx, b.tsx\ngettext("Say \\"hi\\"");\n',
    );
    expect(js).toContain('ngettext("one", "many", 1);\n');
    expect(js).toContain('pgettext("verb", "Clone");\n');
    expect(js).toContain('npgettext("list", "one", "many", 1);\n');
  });
});

describe("the React apps' messages", () => {
  const files = sourceFiles();

  it("come from every package's sources except Smarter Chat's, tests, stories and mocks, and static/js", () => {
    expect(files.some((f) => f.includes("/packages/smarter-secret-list/src/App.tsx"))).toBe(true);
    expect(files.some((f) => f.endsWith("/smarter/static/js/account/authentication/sign-in.js"))).toBe(true);
    expect(files.some((f) => f.includes("/packages/smarter-chat/"))).toBe(false);
    expect(files.some((f) => /\.(test|stories)\.tsx?$|\/mocks\/|\.d\.ts$/.test(f))).toBe(false);
  });

  it("are merged, with every file that uses them", () => {
    const messages = extractMessages(files);
    const keys = messages.map((m) => JSON.stringify([m.context, m.singular, m.plural]));
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("are up to date in i18n/messages.js: run `make i18n-messages`", () => {
    expect(fs.readFileSync(MESSAGES_FILE, "utf-8")).toBe(formatMessages(extractMessages(files)));
  });
});
