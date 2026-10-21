/**
 * Updates Smarter Chat's message catalogs: extracts the messages that src/ marks for translation, merges them
 * into each language's .po file, and compiles the .po files into src/catalogs.gen.ts, which the builds bundle.
 *
 * Smarter Chat marks its messages with gettext(), ngettext(), pgettext() and npgettext() from src/lib/i18n.tsx.
 * GNU xgettext can't parse TypeScript and JSX, so the calls are found with the TypeScript compiler instead, as the
 * Smarter web console's smarter/react/i18n/extract.ts finds its React apps' calls. Each message's argument must be a
 * string literal, or a concatenation of them: anything else is an error, with its file and line.
 *
 * - locale/smarter-chat.pot: the template, every message with an empty translation.
 * - locale/<language>/LC_MESSAGES/smarter-chat.po: each language's catalog. New messages are added with an empty
 *   translation, translations of messages that are still used are kept, and the others are dropped. A language in
 *   LANGUAGES that has no catalog yet gets a new one.
 * - src/catalogs.gen.ts: the translated messages of every catalog, and each language's plural rule, as code.
 *
 * A "Translators:" comment on the line before a call, or earlier on the same line, is copied into the catalogs,
 * with the files that use the message. No dates are written, so that a run that changes no message changes no file.
 *
 *     npm run i18n                    # writes the catalogs
 *     node scripts/i18n.mjs --check   # exits 1 if a catalog is out of date
 *
 * src/catalogs.test.ts fails when a catalog is out of date, or has a message that isn't translated.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const SRC_DIR = path.join(root, "src");
export const LOCALE_DIR = path.join(root, "locale");
export const DOMAIN = "smarter-chat";
export const TEMPLATE_PATH = path.join(LOCALE_DIR, `${DOMAIN}.pot`);
export const CATALOGS_PATH = path.join(SRC_DIR, "catalogs.gen.ts");

/**
 * The languages that Smarter Chat is translated into, other than English, its source language: the Smarter web
 * console's. Spanish is Latin American Spanish, under the generic "es" code, so that every variant of Spanish
 * that a page or a browser asks for gets it. Brazilian Portuguese is under its locale name, pt_BR, the web console's
 * pt-br. These are used only to create a language's catalog.
 */
export const LANGUAGES = {
  es: { team: "Latin American Spanish", pluralForms: "nplurals=2; plural=(n != 1);" },
  fr: { team: "French", pluralForms: "nplurals=2; plural=(n > 1);" },
  pt_BR: { team: "Brazilian Portuguese", pluralForms: "nplurals=2; plural=(n > 1);" },
};

/** The translation functions, and the positions of their context, singular and plural arguments. */
const KEYWORDS = {
  gettext: { singular: 0 },
  ngettext: { singular: 0, plural: 1 },
  pgettext: { context: 0, singular: 1 },
  npgettext: { context: 0, singular: 1, plural: 2 },
};

// gettext's separator of a message's context and its msgid, in a compiled catalog.
const CONTEXT_SEPARATOR = "\u0004";
// the characters of a Plural-Forms expression, which is compiled into code.
const PLURAL_EXPRESSION = /^[\sn0-9?:=!<>%&|()]+$/;

/** A gettext() call whose message isn't a string literal, so it can't be extracted. */
export class ExtractionError extends Error {}

/** The source files to extract from: src/, except tests, stories, mocks and generated files. */
export function sourceFiles(dir = SRC_DIR) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "mocks") files.push(...sourceFiles(full));
    } else if (/\.tsx?$/.test(entry.name) && !/\.(test|stories)\.tsx?$|\.d\.ts$|\.gen\.ts$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

/** The value of a string literal, a template literal without substitutions, or a concatenation of them. */
function literalValue(node) {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isParenthesizedExpression(node)) return literalValue(node.expression);
  if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    const left = literalValue(node.left);
    const right = literalValue(node.right);
    return left !== undefined && right !== undefined ? left + right : undefined;
  }
  return undefined;
}

/**
 * The file's "Translators:" comments, // or /* *\/, including those in JSX, {/* ... *\/}, with the line that each
 * ends on and the position of its end.
 */
function translatorComments(source) {
  const comments = [];
  for (const match of source.text.matchAll(/\/\/[^\n]*|\/\*[\s\S]*?\*\//g)) {
    const text = match[0]
      .replace(/^\/\/|^\/\*+|\*+\/$/g, "")
      .split("\n")
      .map((line) => line.replace(/^\s*\*?\s?/, "").trim())
      .filter(Boolean)
      .join(" ");
    if (!text.startsWith("Translators:")) continue;
    const end = match.index + match[0].length;
    comments.push({ text, end, line: source.getLineAndCharacterOfPosition(end).line });
  }
  return comments;
}

/**
 * The messages of one file's source text, as { context?, singular, plural?, files, comments }. `file` is the path
 * written to the catalogs. A comment applies to the calls after it on the line that it ends on, and on the next.
 */
export function extractFromSource(file, sourceText) {
  const source = ts.createSourceFile(file, sourceText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const comments = translatorComments(source);
  const messages = [];
  const commentsFor = (start) => {
    const line = source.getLineAndCharacterOfPosition(start).line;
    return comments.filter((c) => c.line === line - 1 || (c.line === line && c.end <= start)).map((c) => c.text);
  };
  const visit = (node) => {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text in KEYWORDS) {
      const keyword = KEYWORDS[node.expression.text];
      const argument = (index) => {
        const value = node.arguments[index] ? literalValue(node.arguments[index]) : undefined;
        if (value === undefined) {
          const { line, character } = source.getLineAndCharacterOfPosition(node.getStart(source));
          throw new ExtractionError(
            `${file}:${line + 1}:${character + 1}: argument ${index + 1} of ${node.expression.text}() ` +
              "must be a string literal, so that it can be extracted for translation. Use interpolate() for values.",
          );
        }
        return value;
      };
      const message = { singular: argument(keyword.singular), files: [file], comments: commentsFor(node.getStart()) };
      if (keyword.context !== undefined) message.context = argument(keyword.context);
      if (keyword.plural !== undefined) message.plural = argument(keyword.plural);
      messages.push(message);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return messages;
}

/** The key of a message in a catalog: its context and its msgid. */
function messageKey(context, msgid) {
  return context === undefined ? msgid : `${context}${CONTEXT_SEPARATOR}${msgid}`;
}

/** Extracts and merges the messages of many files, in the order that they first occur. */
export function extractMessages(files = sourceFiles()) {
  const merged = new Map();
  for (const file of files) {
    const relative = path.relative(root, file).split(path.sep).join("/");
    for (const message of extractFromSource(relative, fs.readFileSync(file, "utf-8"))) {
      const key = messageKey(message.context, message.singular);
      const existing = merged.get(key);
      if (!existing) {
        merged.set(key, message);
        continue;
      }
      if ((existing.plural ?? null) !== (message.plural ?? null)) {
        throw new ExtractionError(`${relative}: "${message.singular}" has two different plural forms.`);
      }
      for (const f of message.files) if (!existing.files.includes(f)) existing.files.push(f);
      for (const c of message.comments) if (!existing.comments.includes(c)) existing.comments.push(c);
    }
  }
  return [...merged.values()];
}

/** A .po string's value: the concatenation of its quoted parts. */
function unquote(quoted) {
  return JSON.parse(quoted);
}

/** A .po string, quoted, split after its newlines, as GNU gettext writes them. */
function quote(keyword, value) {
  const escaped = (text) => JSON.stringify(text);
  const lines = value.split(/(?<=\n)/).filter((line) => line !== "");
  if (lines.length <= 1) return [`${keyword} ${escaped(value)}`];
  return [`${keyword} ""`, ...lines.map(escaped)];
}

/**
 * Parses a .po file into its header's fields and its entries, as
 * { context?, msgid, plural?, msgstr: string[], comments, references, flags }. Obsolete entries (#~) are ignored.
 */
export function parsePo(text) {
  const entries = [];
  // the entry being read, and the field that a continuation line ("...") adds to.
  let entry = null;
  let field = null;
  const current = () => (entry ??= { comments: [], references: [], flags: [], msgstr: [] });
  // an entry ends at a blank line, or where the next one's comments, msgctxt or msgid start.
  const finish = () => {
    if (entry?.msgid !== undefined) {
      entries.push(entry);
      entry = null;
    }
    field = null;
  };
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (line === "" || line.startsWith("#~")) {
      finish();
      continue;
    }
    if (line.startsWith("#")) {
      finish();
      if (line.startsWith("#.")) current().comments.push(line.slice(2).trim());
      else if (line.startsWith("#:")) current().references.push(...line.slice(2).trim().split(/\s+/));
      else if (line.startsWith("#,"))
        current().flags.push(
          ...line
            .slice(2)
            .split(",")
            .map((flag) => flag.trim()),
        );
      else current();
      continue;
    }
    const keyword = /^(msgctxt|msgid_plural|msgid|msgstr(?:\[(\d+)\])?)\s+(".*")$/.exec(line);
    if (keyword) {
      if (keyword[1] === "msgctxt" || (keyword[1] === "msgid" && entry?.context === undefined)) finish();
      current();
      const value = unquote(keyword[3]);
      if (keyword[1] === "msgctxt") field = { name: "context" };
      else if (keyword[1] === "msgid") field = { name: "msgid" };
      else if (keyword[1] === "msgid_plural") field = { name: "plural" };
      else field = { name: "msgstr", index: keyword[2] === undefined ? 0 : Number(keyword[2]) };
      if (field.name === "msgstr") entry.msgstr[field.index] = value;
      else entry[field.name] = value;
      continue;
    }
    if (line.startsWith('"') && field && typeof field === "object") {
      const value = unquote(line);
      if (field.name === "msgstr") entry.msgstr[field.index] += value;
      else entry[field.name] += value;
      continue;
    }
    throw new Error(`Can't parse this line of a .po file: ${raw}`);
  }
  finish();
  const headerEntry = entries.find((e) => e.msgid === "" && e.context === undefined);
  const header = {};
  for (const headerLine of (headerEntry?.msgstr[0] ?? "").split("\n")) {
    const separator = headerLine.indexOf(":");
    if (separator > 0) header[headerLine.slice(0, separator).trim()] = headerLine.slice(separator + 1).trim();
  }
  return { header, headerComments: headerEntry?.comments ?? [], entries: entries.filter((e) => e !== headerEntry) };
}

/** The number of plural forms in a Plural-Forms header, e.g. 2 for "nplurals=2; plural=(n != 1);". */
function pluralCount(pluralForms) {
  return Number(/nplurals\s*=\s*(\d+)/.exec(pluralForms ?? "")?.[1] ?? 2);
}

/** The header's lines, in order, for a catalog of a language, or for the template. */
function headerLines(language, header) {
  const fields = {
    "Project-Id-Version": "Smarter Chat",
    "Report-Msgid-Bugs-To": "https://github.com/smarter-sh/smarter-chat/issues",
    "Last-Translator": header["Last-Translator"] ?? "The Smarter Project",
    "Language-Team": header["Language-Team"] ?? LANGUAGES[language]?.team ?? "",
    Language: language ?? "",
    "MIME-Version": "1.0",
    "Content-Type": "text/plain; charset=UTF-8",
    "Content-Transfer-Encoding": "8bit",
    "Plural-Forms": header["Plural-Forms"] ?? LANGUAGES[language]?.pluralForms ?? "nplurals=2; plural=(n != 1);",
  };
  return Object.entries(fields).map(([name, value]) => `${name}: ${value}\n`);
}

/** Renders a catalog: the template when language is null, else a language's, with the translations it had. */
export function formatPo(messages, language = null, existing = { header: {}, entries: [] }) {
  const translations = new Map(existing.entries.map((e) => [messageKey(e.context, e.msgid), e.msgstr]));
  const nplurals = pluralCount(existing.header["Plural-Forms"] ?? LANGUAGES[language]?.pluralForms);
  const title = language
    ? `${LANGUAGES[language]?.team ?? existing.header["Language-Team"] ?? language} messages of Smarter Chat.`
    : "The messages of Smarter Chat: the template of its catalogs.";
  const lines = [
    `# ${title}`,
    "# Don't edit the msgids here: change the source, then run `npm run i18n`.",
    "# This file is distributed under the same license as the @smarter.sh/ui-chat package (AGPL-3.0).",
    "#",
    'msgid ""',
    'msgstr ""',
    ...headerLines(language, existing.header).map((line) => JSON.stringify(line)),
  ];
  for (const message of messages) {
    lines.push("");
    for (const comment of message.comments) lines.push(`#. ${comment}`);
    lines.push(`#: ${message.files.join(" ")}`);
    const msgstr = (language && translations.get(messageKey(message.context, message.singular))) || [];
    if (message.context !== undefined) lines.push(...quote("msgctxt", message.context));
    lines.push(...quote("msgid", message.singular));
    if (message.plural !== undefined) {
      lines.push(...quote("msgid_plural", message.plural));
      const count = language ? nplurals : 2;
      for (let index = 0; index < count; index++) lines.push(...quote(`msgstr[${index}]`, msgstr[index] ?? ""));
    } else {
      lines.push(...quote("msgstr", msgstr[0] ?? ""));
    }
  }
  return lines.join("\n") + "\n";
}

/** The code of a Plural-Forms header's plural rule, e.g. "(n > 1)", checked to be an arithmetic expression of n. */
export function pluralRule(pluralForms) {
  const expression = /plural\s*=\s*([^;]+);?/.exec(pluralForms ?? "")?.[1]?.trim();
  if (!expression || !PLURAL_EXPRESSION.test(expression)) {
    throw new Error(`Not a valid Plural-Forms header: ${JSON.stringify(pluralForms)}`);
  }
  return expression;
}

/** Renders src/catalogs.gen.ts from the languages' parsed catalogs, by language. */
export function formatCatalogs(catalogs) {
  const lines = [
    "/**",
    " * Smarter Chat's message catalogs: generated from locale/<language>/LC_MESSAGES/smarter-chat.po by",
    " * scripts/i18n.mjs. Do not edit; run `npm run i18n`. See src/lib/i18n.tsx.",
    " */",
    "",
    "/** A language's translated messages, by msgid (context, \\u0004, msgid in a context), and its plural rule. */",
    "export interface Catalog {",
    "  /** The index of the plural form for a count. */",
    "  plural: (n: number) => number;",
    "  /** A message's translation, or its plural forms' translations. */",
    "  messages: Record<string, string | string[]>;",
    "}",
    "",
    "export const CATALOGS: Record<string, Catalog> = {",
  ];
  for (const [language, catalog] of Object.entries(catalogs)) {
    lines.push(`  ${JSON.stringify(language)}: {`);
    lines.push(`    plural: (n: number) => Number(${pluralRule(catalog.header["Plural-Forms"])}),`);
    lines.push("    messages: {");
    for (const entry of catalog.entries) {
      if (entry.flags.includes("fuzzy") || entry.msgstr.every((value) => !value)) continue;
      const value = entry.plural === undefined ? entry.msgstr[0] : entry.msgstr;
      lines.push(`      ${JSON.stringify(messageKey(entry.context, entry.msgid))}: ${JSON.stringify(value)},`);
    }
    lines.push("    },");
    lines.push("  },");
  }
  lines.push("};");
  return lines.join("\n") + "\n";
}

/** The catalog of a language. */
export function catalogPath(language) {
  return path.join(LOCALE_DIR, language, "LC_MESSAGES", `${DOMAIN}.po`);
}

/** The languages that have a catalog, or are in LANGUAGES. */
export function catalogLanguages() {
  const existing = fs.existsSync(LOCALE_DIR)
    ? fs.readdirSync(LOCALE_DIR).filter((name) => fs.existsSync(catalogPath(name)))
    : [];
  return [...new Set([...Object.keys(LANGUAGES), ...existing])].sort();
}

/** Every file that this script writes, by its path, with its new content. */
export function generatedFiles() {
  const messages = extractMessages();
  const files = new Map([[TEMPLATE_PATH, formatPo(messages)]]);
  const catalogs = {};
  for (const language of catalogLanguages()) {
    const file = catalogPath(language);
    const existing = fs.existsSync(file) ? parsePo(fs.readFileSync(file, "utf-8")) : { header: {}, entries: [] };
    const po = formatPo(messages, language, existing);
    files.set(file, po);
    catalogs[language] = parsePo(po);
  }
  files.set(CATALOGS_PATH, formatCatalogs(catalogs));
  return files;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const files = generatedFiles();
  const changed = [...files].filter(
    ([file, content]) => !fs.existsSync(file) || fs.readFileSync(file, "utf-8") !== content,
  );
  if (process.argv.includes("--check")) {
    if (changed.length > 0) {
      for (const [file] of changed) console.error(`${path.relative(root, file)} is out of date. Run \`npm run i18n\`.`);
      process.exit(1);
    }
  } else {
    for (const [file, content] of changed) {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, content);
      console.log(`wrote ${path.relative(root, file)}`);
    }
  }
}
