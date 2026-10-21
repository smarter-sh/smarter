/**
 * Smarter Chat's message catalogs: locale/smarter-chat.pot, locale/<language>/LC_MESSAGES/smarter-chat.po, and
 * src/catalogs.gen.ts, which scripts/i18n.mjs generates from the source and the .po files.
 *
 * - They must be current: every message that src/ marks is in every catalog, and no other.
 * - Every message must be translated, with the same placeholders as its English text.
 * - The extractor must find every kind of call, and refuse a message that isn't a string literal.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  ExtractionError,
  catalogLanguages,
  catalogPath,
  extractFromSource,
  formatCatalogs,
  formatPo,
  parsePo,
  pluralRule,
} from "../scripts/i18n.mjs";

const root = path.resolve(import.meta.dirname, "..");

const placeholders = (text: string) => [...text.matchAll(/%\(\w+\)s/g)].map(([placeholder]) => placeholder).sort();

describe("the message catalogs", () => {
  it("are current", () => {
    expect(() =>
      execFileSync(process.execPath, [path.join(root, "scripts", "i18n.mjs"), "--check"], { stdio: "pipe" }),
    ).not.toThrow();
  });

  it("are the Smarter web console's languages", () => {
    expect(catalogLanguages()).toEqual(["es", "fr", "pt_BR"]);
  });

  it.each(["es", "fr", "pt_BR"])("translate every message into %s, with its placeholders", (language) => {
    const { header, entries } = parsePo(fs.readFileSync(catalogPath(language), "utf-8"));
    expect(header.Language).toBe(language);
    const nplurals = Number(/nplurals=(\d+)/.exec(header["Plural-Forms"])?.[1]);
    const problems: string[] = [];
    for (const entry of entries) {
      if (entry.flags.includes("fuzzy")) problems.push(`fuzzy: ${entry.msgid}`);
      const forms = entry.plural === undefined ? 1 : nplurals;
      for (let index = 0; index < forms; index++) {
        const translation = entry.msgstr[index] ?? "";
        if (!translation) problems.push(`not translated: ${entry.msgid}`);
        else if (placeholders(translation).join() !== placeholders(entry.msgid).join()) {
          problems.push(`placeholders: ${entry.msgid} -> ${translation}`);
        }
      }
    }
    expect(problems).toEqual([]);
    // the chat's own messages, e.g. its buttons' labels: a catalog that parsed to almost nothing is broken.
    expect(entries.length).toBeGreaterThan(30);
  });
});

describe("extractFromSource", () => {
  it("extracts each kind of call, in JSX, template literals and concatenations", () => {
    const source = `
      const a = gettext("Close");
      const b = ngettext("%(count)s tool", "%(count)s tools", n);
      const c = pgettext("button", "Code");
      const d = npgettext("list", "one row", "%(count)s rows", n);
      const App = () => <p title={gettext(\`Title\`)}>{gettext("Long " + "message")}</p>;
      window.django.gettext(msgid); obj.gettext("y"); translate("z");
    `;
    expect(extractFromSource("App.tsx", source)).toEqual([
      { singular: "Close", files: ["App.tsx"], comments: [] },
      { singular: "%(count)s tool", plural: "%(count)s tools", files: ["App.tsx"], comments: [] },
      { context: "button", singular: "Code", files: ["App.tsx"], comments: [] },
      { context: "list", singular: "one row", plural: "%(count)s rows", files: ["App.tsx"], comments: [] },
      { singular: "Title", files: ["App.tsx"], comments: [] },
      { singular: "Long message", files: ["App.tsx"], comments: [] },
    ]);
  });

  it("keeps the translator comments on the line before, or earlier on the same line", () => {
    const source = `
      // Translators: the button that opens the docs
      const a = gettext("Docs");
      const b = /* Translators: a verb */ gettext("Copy");
      const c = (
        <p>
          {/* Translators: a noun */}
          {gettext("Diagram")}
        </p>
      );
      // an unrelated comment
      const d = gettext("Close");
    `;
    expect(extractFromSource("App.tsx", source).map((message) => message.comments)).toEqual([
      ["Translators: the button that opens the docs"],
      ["Translators: a verb"],
      ["Translators: a noun"],
      [],
    ]);
  });

  it("refuses a message that isn't a string literal, with its file and line", () => {
    expect(() => extractFromSource("App.tsx", "\nconst a = gettext(label);")).toThrow(ExtractionError);
    expect(() => extractFromSource("App.tsx", "\nconst a = gettext(label);")).toThrow(/^App\.tsx:2:11: argument 1/);
    expect(() => extractFromSource("App.tsx", "gettext(`Close ${label}`);")).toThrow(ExtractionError);
    expect(() => extractFromSource("App.tsx", 'ngettext("one", plural, n);')).toThrow(/argument 2 of ngettext/);
  });
});

describe("parsePo and formatPo", () => {
  const messages = [
    { singular: "Close", files: ["a.tsx"], comments: ["Translators: a verb"] },
    { context: "button", singular: "Code", files: ["a.tsx", "b.ts"], comments: [] },
    { singular: "%(count)s tool", plural: "%(count)s tools", files: ["b.ts"], comments: [] },
    { singular: "A long message\nin two lines", files: ["b.ts"], comments: [] },
  ];

  it("write a template with empty translations", () => {
    const { header, entries } = parsePo(formatPo(messages));
    expect(header["Project-Id-Version"]).toBe("Smarter Chat");
    expect(entries.map((entry) => [entry.context, entry.msgid, entry.plural, entry.msgstr])).toEqual([
      [undefined, "Close", undefined, [""]],
      ["button", "Code", undefined, [""]],
      [undefined, "%(count)s tool", "%(count)s tools", ["", ""]],
      [undefined, "A long message\nin two lines", undefined, [""]],
    ]);
    expect(entries[0].comments).toEqual(["Translators: a verb"]);
    expect(entries[1].references).toEqual(["a.tsx", "b.ts"]);
  });

  it("keep a language's translations of the messages that are still used, and drop the others", () => {
    const existing = parsePo(
      [
        'msgid ""',
        'msgstr ""',
        '"Language: fr\\n"',
        '"Plural-Forms: nplurals=2; plural=(n > 1);\\n"',
        "",
        "#, fuzzy",
        'msgctxt "button"',
        'msgid "Code"',
        'msgstr "Code"',
        "",
        'msgid "%(count)s tool"',
        'msgid_plural "%(count)s tools"',
        'msgstr[0] "%(count)s outil"',
        'msgstr[1] ""',
        '"%(count)s outils"',
        "",
        '#~ msgid "Obsolete"',
        '#~ msgstr "Obsolète"',
        'msgid "Gone"',
        'msgstr "Parti"',
      ].join("\n"),
    );
    expect(existing.entries[0].flags).toEqual(["fuzzy"]);
    const { entries } = parsePo(formatPo(messages, "fr", existing));
    expect(entries.map((entry) => entry.msgstr)).toEqual([
      [""],
      ["Code"],
      ["%(count)s outil", "%(count)s outils"],
      [""],
    ]);
  });

  it("refuse a line that isn't gettext", () => {
    expect(() => parsePo('msgid "Close"\nmsgstr "Fermer"\nnonsense')).toThrow(/Can't parse/);
  });
});

describe("formatCatalogs", () => {
  it("compiles the translated messages, and each language's plural rule", () => {
    const catalog = parsePo(
      [
        'msgid ""',
        'msgstr "Plural-Forms: nplurals=2; plural=(n > 1);\\n"',
        "",
        'msgid "Close"',
        'msgstr "Fermer"',
        "",
        'msgid "Untranslated"',
        'msgstr ""',
        "",
        "#, fuzzy",
        'msgid "Fuzzy"',
        'msgstr "Flou"',
        "",
        'msgctxt "button"',
        'msgid "Code"',
        'msgstr "Code"',
      ].join("\n"),
    );
    const code = formatCatalogs({ fr: catalog });
    expect(code).toContain("plural: (n: number) => Number((n > 1)),");
    expect(code).toContain('"Close": "Fermer",');
    expect(code).toContain('"button\\u0004Code": "Code",');
    expect(code).not.toContain("Untranslated");
    expect(code).not.toContain("Flou");
  });

  it("compiles only a plural rule that is arithmetic of n", () => {
    expect(pluralRule("nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 ? 1 : 2);")).toBe(
      "(n==1 ? 0 : n%10>=2 && n%10<=4 ? 1 : 2)",
    );
    expect(() => pluralRule("nplurals=2; plural=alert(1);")).toThrow(/Not a valid Plural-Forms/);
    expect(() => pluralRule(undefined)).toThrow(/Not a valid Plural-Forms/);
  });
});
