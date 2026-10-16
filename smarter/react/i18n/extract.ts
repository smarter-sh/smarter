/**
 * Extracts the React apps' translatable messages for Django's makemessages.
 *
 * The web console's React apps mark their messages with gettext(), ngettext(), pgettext() and
 * npgettext() from @smarter/common, and its plain JavaScript in smarter/static/js calls the global
 * functions of the same names, which Django's JavaScriptCatalog defines. The xgettext that Django's makemessages runs can't parse
 * TypeScript and JSX, so this script finds those calls with the TypeScript compiler, and writes
 * each distinct message as a plain JavaScript call to i18n/messages.js. makemessages then reads
 * that file for the djangojs domain, and merges it into
 * smarter/smarter/locale/<language>/LC_MESSAGES/djangojs.po like any other source.
 *
 * Each message in messages.js is preceded by a "Translators:" comment that lists the source files
 * that use it, and by the developer's own "Translators:" comment, if the call has one, so
 * translators see both in the .po file.
 *
 * Usage (in smarter/react):
 *
 *   npm run i18n:extract     # writes i18n/messages.js
 *
 * `make i18n-messages` runs it, then makemessages and compilemessages. i18n/extract.test.ts
 * fails when messages.js is out of date.
 */
import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

/** The workspace, smarter/react. */
export const WORKSPACE = path.resolve(import.meta.dirname, "..");

/** The Django project, smarter/: the paths shown to translators are relative to it. */
export const PROJECT_ROOT = path.resolve(WORKSPACE, "..");

/** The web console's own plain JavaScript, which calls the gettext() that Django's catalog defines. */
export const STATIC_JS_DIR = path.join(PROJECT_ROOT, "smarter", "static", "js");

/** The generated file that makemessages reads. */
export const MESSAGES_FILE = path.join(WORKSPACE, "i18n", "messages.js");

/**
 * Packages whose messages aren't extracted. Smarter Chat is its own repository, cloned into the
 * workspace, and is published to npm for sites other than the web console.
 */
const EXCLUDED_PACKAGES = new Set(["smarter-chat"]);

/** The translation functions, and the positions of their context, singular and plural arguments. */
const KEYWORDS: Record<string, { context?: number; singular: number; plural?: number }> = {
  gettext: { singular: 0 },
  ngettext: { singular: 0, plural: 1 },
  pgettext: { context: 0, singular: 1 },
  npgettext: { context: 0, singular: 1, plural: 2 },
};

/** One translatable message, with the files that use it and their translator comments. */
export interface Message {
  context?: string;
  singular: string;
  plural?: string;
  files: string[];
  comments: string[];
}

/** A gettext() call whose message isn't a string literal, so it can't be extracted. */
export class ExtractionError extends Error {}

/**
 * The source files to extract from: every package's src/, except tests, stories and mocks, then
 * the web console's plain JavaScript in smarter/static/js.
 */
export function sourceFiles(workspace: string = WORKSPACE, staticJsDir: string = STATIC_JS_DIR): string[] {
  const files: string[] = [];
  const walk = (dir: string, pattern: RegExp) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== "mocks" && entry.name !== "node_modules") walk(full, pattern);
      } else if (pattern.test(entry.name) && !/\.(test|stories)\.tsx?$|\.d\.ts$/.test(entry.name)) {
        files.push(full);
      }
    }
  };
  const packagesDir = path.join(workspace, "packages");
  for (const pkg of fs.readdirSync(packagesDir).sort()) {
    const src = path.join(packagesDir, pkg, "src");
    if (!EXCLUDED_PACKAGES.has(pkg) && fs.existsSync(src)) walk(src, /\.tsx?$/);
  }
  if (fs.existsSync(staticJsDir)) walk(staticJsDir, /\.js$/);
  return files;
}

/** The value of a string literal, a template literal without substitutions, or a concatenation of them. */
function literalValue(node: ts.Expression): string | undefined {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isParenthesizedExpression(node)) return literalValue(node.expression);
  if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    const left = literalValue(node.left);
    const right = literalValue(node.right);
    return left !== undefined && right !== undefined ? left + right : undefined;
  }
  return undefined;
}

/** A "Translators:" comment, and the position of its end. */
interface TranslatorComment {
  text: string;
  end: number;
  line: number;
}

/**
 * The file's "Translators:" comments, // or /* *\/, including those in JSX, {/* ... *\/}. A comment
 * applies to the calls on the line that it ends on, after it, and to those on the next line.
 */
function translatorCommentsOf(source: ts.SourceFile): TranslatorComment[] {
  const comments: TranslatorComment[] = [];
  for (const match of source.text.matchAll(/\/\/[^\n]*|\/\*[\s\S]*?\*\//g)) {
    const text = match[0]
      .replace(/^\/\/|^\/\*+|\*+\/$/g, "")
      .split("\n")
      .map((line) => line.replace(/^\s*\*?\s?/, "").trim())
      .filter(Boolean)
      .join(" ");
    if (!text.startsWith("Translators:")) continue;
    const end = (match.index ?? 0) + match[0].length;
    comments.push({ text, end, line: source.getLineAndCharacterOfPosition(end).line });
  }
  return comments;
}

/** Extracts the messages of one file's source text. `file` is the path shown to translators. */
export function extractFromSource(file: string, sourceText: string): Message[] {
  const kind = file.endsWith(".js") ? ts.ScriptKind.JS : ts.ScriptKind.TSX;
  const source = ts.createSourceFile(file, sourceText, ts.ScriptTarget.Latest, true, kind);
  const comments = translatorCommentsOf(source);
  const messages: Message[] = [];
  const commentsFor = (start: number): string[] => {
    const line = source.getLineAndCharacterOfPosition(start).line;
    return comments.filter((c) => c.line === line - 1 || (c.line === line && c.end <= start)).map((c) => c.text);
  };
  const visit = (node: ts.Node) => {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text in KEYWORDS) {
      const keyword = KEYWORDS[node.expression.text];
      const argument = (index: number | undefined): string | undefined => {
        if (index === undefined) return undefined;
        const value = node.arguments[index] ? literalValue(node.arguments[index]) : undefined;
        if (value === undefined) {
          const { line, character } = source.getLineAndCharacterOfPosition(node.getStart(source));
          throw new ExtractionError(
            `${file}:${line + 1}:${character + 1}: argument ${index + 1} of ${node.expression.getText(source)}() ` +
              "must be a string literal, so that it can be extracted for translation. Use interpolate() for values.",
          );
        }
        return value;
      };
      const message: Message = {
        singular: argument(keyword.singular) as string,
        files: [file],
        comments: commentsFor(node.getStart(source)),
      };
      if (keyword.context !== undefined) message.context = argument(keyword.context);
      if (keyword.plural !== undefined) message.plural = argument(keyword.plural);
      messages.push(message);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return messages;
}

/** Extracts and merges the messages of many files, in the order that they first occur. */
export function extractMessages(files: string[], root: string = PROJECT_ROOT): Message[] {
  const merged = new Map<string, Message>();
  for (const file of files) {
    const relative = path.relative(root, file).split(path.sep).join("/");
    for (const message of extractFromSource(relative, fs.readFileSync(file, "utf-8"))) {
      const key = JSON.stringify([message.context ?? null, message.singular, message.plural ?? null]);
      const existing = merged.get(key);
      if (!existing) {
        merged.set(key, message);
        continue;
      }
      for (const f of message.files) if (!existing.files.includes(f)) existing.files.push(f);
      for (const c of message.comments) if (!existing.comments.includes(c)) existing.comments.push(c);
    }
  }
  return [...merged.values()];
}

/** Renders the messages as the JavaScript that makemessages reads. */
export function formatMessages(messages: Message[]): string {
  const lines = [
    "// Generated by `npm run i18n:extract` (smarter/react/i18n/extract.ts) from the React apps'",
    "// gettext() calls. Don't edit it: run `make i18n-messages`. Django's makemessages reads it",
    "// for the djangojs domain. It is never loaded by a browser.",
    "",
  ];
  for (const message of messages) {
    for (const comment of message.comments) lines.push(`// ${comment}`);
    lines.push(`// Translators: used in ${message.files.join(", ")}`);
    const q = (value: string) => JSON.stringify(value);
    if (message.context !== undefined && message.plural !== undefined) {
      lines.push(`npgettext(${q(message.context)}, ${q(message.singular)}, ${q(message.plural)}, 1);`);
    } else if (message.context !== undefined) {
      lines.push(`pgettext(${q(message.context)}, ${q(message.singular)});`);
    } else if (message.plural !== undefined) {
      lines.push(`ngettext(${q(message.singular)}, ${q(message.plural)}, 1);`);
    } else {
      lines.push(`gettext(${q(message.singular)});`);
    }
  }
  return lines.join("\n") + "\n";
}

if (import.meta.main) {
  const messages = extractMessages(sourceFiles());
  fs.writeFileSync(MESSAGES_FILE, formatMessages(messages));
  console.log(`Wrote ${messages.length} messages to ${path.relative(process.cwd(), MESSAGES_FILE)}`);
}
