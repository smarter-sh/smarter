/**
 * Source code in the resource detail: the charcoal block, with line numbers, that the Manifest tab and the Details
 * tab's code fields share, and the small highlighters that color its lines: JSON, CSS and SQL here, and YAML in
 * ./yaml. Each takes text that is already formatted (see prettyJson, styleObjectAsCss and asYaml in DetailFields,
 * and a SqlPlugin's formatSql), one line at a time, and returns each line as highlighted spans.
 */
import { Fragment, type ReactNode } from "react";

/** A line of code, as text and highlighted spans. */
export type CodeLine = ReactNode[];

/**
 * How a token is highlighted: a class name, null for plain text, or a function of the match and the text after it
 * that returns one of those.
 */
type TokenClass = string | null | ((match: string, rest: string) => string | null);

/** A rule of a highlighter: a sticky pattern, and how what it matches is highlighted. */
type Rule = [RegExp, TokenClass];

/** A token, as a highlighted span. */
const span = (className: string, text: string, key: number) => (
  <span key={key} className={className}>
    {text}
  </span>
);

/**
 * A line, as spans: at each position, the first rule whose pattern matches there highlights what it matches, and
 * text that no rule matches is left plain.
 */
export function tokenize(line: string, rules: Rule[]): CodeLine {
  const tokens: CodeLine = [];
  let plain = "";
  const flush = () => {
    if (plain) tokens.push(plain);
    plain = "";
  };
  let at = 0;
  next: while (at < line.length) {
    for (const [pattern, tokenClass] of rules) {
      pattern.lastIndex = at;
      const match = pattern.exec(line)?.[0];
      if (!match) continue;
      const className =
        typeof tokenClass === "function" ? tokenClass(match, line.slice(at + match.length)) : tokenClass;
      if (className) {
        flush();
        tokens.push(span(className, match, tokens.length));
      } else {
        plain += match;
      }
      at += match.length;
      continue next;
    }
    plain += line[at++];
  }
  flush();
  return tokens;
}

/** The lines of a text, without the newline at its end. */
const linesOf = (text: string) => text.replace(/\n$/, "").split("\n");

/** Code that has no highlighter, e.g. a regular expression or a shell command: its lines, plain. */
export function plainLines(text: string): CodeLine[] {
  return linesOf(text).map((line) => [line]);
}

const JSON_RULES: Rule[] = [
  [/"(?:[^"\\]|\\.)*"(?=\s*:)/y, "code-key"],
  [/"(?:[^"\\]|\\.)*"/y, "code-string"],
  [/-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?/y, "code-number"],
  [/\b(?:true|false|null)\b/y, "code-literal"],
  [/[{}[\],:]/y, "code-punctuation"],
];

/** JSON, highlighted: keys, strings, numbers, true, false and null. */
export function highlightJson(json: string): CodeLine[] {
  return linesOf(json).map((line) => tokenize(line, JSON_RULES));
}

/** The rules of a CSS value, e.g. url("..."), #231f20, rgba(255, 255, 255, 0.88) or 8px. */
const CSS_VALUE_RULES: Rule[] = [
  [/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/y, "code-string"],
  [/#[0-9a-fA-F]{3,8}\b/y, "code-number"],
  [/[a-zA-Z-]+(?=\()/y, "code-function"],
  [/!important\b/y, "code-keyword"],
  [/[a-zA-Z_][\w-]*/y, null],
  [/-?\d*\.?\d+(?:[a-zA-Z%]+)?/y, "code-number"],
  [/[(),/]/y, "code-punctuation"],
];

/** One line of CSS, as Prettier formats it: a selector and its brace, a declaration, a closing brace, or a comment. */
function highlightCssLine(line: string): CodeLine {
  if (/^\s*\/\*.*\*\/\s*$/.test(line)) return [span("code-comment", line, 0)];
  const rule = line.match(/^(\s*)([^{};\s][^{};]*?)(\s*)(\{)$/);
  if (rule) {
    const [, indent, selector, space, brace] = rule;
    return [indent, span("code-selector", selector, 1), space, span("code-punctuation", brace, 3)];
  }
  const declaration = line.match(/^(\s*)(-{0,2}[\w-]+)(:)(.*?)(;?)$/);
  if (declaration) {
    const [, indent, property, colon, value, semicolon] = declaration;
    return [
      indent,
      span("code-key", property, 1),
      span("code-punctuation", colon, 2),
      <Fragment key={3}>{tokenize(value, CSS_VALUE_RULES)}</Fragment>,
      semicolon && span("code-punctuation", semicolon, 4),
    ];
  }
  return tokenize(line, [[/[{}]/y, "code-punctuation"]]);
}

/** CSS, highlighted: selectors, properties, strings, colors, numbers and functions. */
export function highlightCss(css: string): CodeLine[] {
  return linesOf(css).map(highlightCssLine);
}

/** The SQL keywords that are highlighted as keywords. Any other word is a name, or a function before a "(". */
const SQL_KEYWORDS = new Set(
  (
    "ALL AND AS ASC BETWEEN BY CASE CROSS DELETE DESC DISTINCT ELSE END EXISTS FROM FULL GROUP HAVING IN INNER " +
    "INSERT INTO IS JOIN LEFT LIKE LIMIT NOT NULL OFFSET ON OR ORDER OUTER RIGHT SELECT SET THEN UNION UPDATE " +
    "USING VALUES WHEN WHERE WITH"
  ).split(" "),
);

const SQL_RULES: Rule[] = [
  [/--.*$/y, "code-comment"],
  [/'(?:[^'\\]|\\.|'')*'/y, "code-string"],
  [/`[^`]*`/y, null],
  // a SqlPlugin's parameter, which the plugin fills in with the LLM's argument.
  [/\{[A-Za-z_][A-Za-z0-9_]*\}/y, "code-param"],
  [/\b(?:TRUE|FALSE)\b/iy, "code-literal"],
  [
    /[A-Za-z_][\w$]*/y,
    (word, rest) => {
      if (SQL_KEYWORDS.has(word.toUpperCase())) return "code-keyword";
      return /^\s*\(/.test(rest) ? "code-function" : null;
    },
  ],
  [/\d+(?:\.\d+)?/y, "code-number"],
  [/[(),;=<>!*+\-/%]+/y, "code-punctuation"],
];

/** SQL, highlighted: keywords, functions, strings, numbers, a SqlPlugin's {parameters}, and comments. */
export function highlightSql(sql: string): CodeLine[] {
  return linesOf(sql).map((line) => tokenize(line, SQL_RULES));
}

export interface CodeBlockProps {
  /** The lines of the code, each highlighted, e.g. by highlightJson(). */
  lines: CodeLine[];
  /** What the code is, for a screen reader, e.g. "Manifest YAML". */
  label: string;
  /** More classes, e.g. one that sets the block's height. */
  className?: string;
}

/** Source code, as the web console shows it everywhere: a charcoal block of numbered, highlighted lines. */
export function CodeBlock({ lines, label, className }: CodeBlockProps) {
  return (
    // a region that scrolls has the focus, so that the keyboard can scroll it.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
    <pre className={`smarter-code-block${className ? ` ${className}` : ""}`} aria-label={label} tabIndex={0}>
      <code>
        {lines.map((tokens, index) => (
          <span key={index} className="smarter-code-line">
            {tokens}
            {"\n"}
          </span>
        ))}
      </code>
    </pre>
  );
}
