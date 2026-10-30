/**
 * The building blocks of a resource's Details tab, which each resource list's DetailView arranges.
 *
 * A DetailView is a column of sections, each a titled card with a grid of labeled fields:
 *
 *   <DetailOverview description={guardrail.description}>
 *     <StatusBar guardrail={guardrail} />
 *   </DetailOverview>
 *   <DetailSection title={gettext("Detection")} icon="scan-barcode">
 *     <DetailField label={gettext("Strategy")} value={guardrail.strategy} />
 *     <DetailField label={gettext("Pattern")} value={guardrail.pattern} type="source" wide />
 *   </DetailSection>
 *   <ResourceMetadataSection resource={guardrail} filtering={filtering} />
 *
 * Exports:
 * - DetailOverview: the resource's description, beside its status and actions.
 * - DetailSection: a titled card of fields.
 * - DetailField: one labeled value, formatted by its type: text, code, url, dateTime, number, bool, json or list.
 * - ResourceMetadataSection: the fields that every resource has: owner, account, dates, version, tags and annotations.
 */
import type { ReactNode } from "react";
import { dump } from "js-yaml";

import type { Annotations, Filtering, Tags, UserProfile } from "../../lib/Types";
import { formatDateTime } from "../../lib/formatDateTime";
import { gettext } from "../../lib/i18n";
import { AnnotationChips, TagChips } from "../MetadataChips";
import { CodeBlock, highlightCss, highlightJson, highlightSql, plainLines } from "./code";
import { highlightYaml } from "./yaml";

/** The reference of formatDateTime()'s relative format, which says how long ago a date was. */
const EPOCH = new Date(0).toISOString();

/**
 * How a DetailField formats its value. code is a short value inline, e.g. a name; json, yaml, css, sql and source are
 * blocks of source code, highlighted but for source, e.g. a regular expression or a shell command. sql is already
 * formatted, e.g. by a SqlPlugin's formatSql().
 */
export type DetailValueType =
  "text" | "code" | "url" | "dateTime" | "number" | "bool" | "json" | "yaml" | "css" | "sql" | "source" | "list";

/** The class of a code block in a field, which keeps it shorter than the Manifest tab's. */
const CODE_FIELD = "smarter-code-block-field";

/** The color of a boolean's "yes": green, or amber or red for a flag that warns, e.g. Suspended. */
export type DetailTone = "success" | "warning" | "danger";

/** The width that Prettier formats to, its printWidth. */
const PRINT_WIDTH = 80;

/**
 * Structured data as JSON, formatted as Prettier formats JSON: an object or array that fits on its line stays on
 * one line, e.g. { "name": "a", "value": 1 }, and one that doesn't has a member per line, indented by two spaces.
 */
export function prettyJson(value: unknown, width: number = PRINT_WIDTH): string {
  const print = (item: unknown, indent: string, prefix: number): string => {
    if (item === null || typeof item !== "object") return JSON.stringify(item) ?? "null";
    const entries: [string | null, unknown][] = Array.isArray(item)
      ? item.map((member) => [null, member])
      : Object.entries(item as Record<string, unknown>);
    const [open, close, pad] = Array.isArray(item) ? ["[", "]", ""] : ["{", "}", " "];
    if (entries.length === 0) return `${open}${close}`;
    const key = (name: string | null) => (name === null ? "" : `${JSON.stringify(name)}: `);
    const flat = `${open}${pad}${entries.map(([name, member]) => key(name) + print(member, "", 0)).join(", ")}${pad}${close}`;
    if (!flat.includes("\n") && indent.length + prefix + flat.length <= width) return flat;
    const inner = `${indent}  `;
    const lines = entries.map(([name, member]) => `${inner}${key(name)}${print(member, inner, key(name).length)}`);
    return `${open}\n${lines.join(",\n")}\n${indent}${close}`;
  };
  return print(value, "", 0);
}

/**
 * Structured data as YAML, formatted as Prettier formats YAML: two-space indents, no wrapped lines, and a text
 * of several lines as a block scalar. A JSON string is parsed first; any other string is shown as it is.
 */
export function asYaml(value: unknown): string {
  let data = value;
  if (typeof value === "string") {
    try {
      data = JSON.parse(value);
    } catch {
      return value;
    }
  }
  return dump(data, { indent: 2, lineWidth: -1, noRefs: true });
}

/** A camelCase key as a CSS name, e.g. backgroundColor as background-color. */
const kebabCase = (key: string) => key.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase();

/** A value as a CSS value: a url as url("..."), a font's name quoted, e.g. "Inter", anything else as it is. */
function cssValue(key: string, value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (/url$/i.test(key) || /^https?:\/\//.test(text)) return `url("${text}")`;
  if (/font/i.test(key) && !/["',]/.test(text)) return `"${text}"`;
  return text;
}

/**
 * A style object, e.g. an LLMClient's spec.config.styles, as CSS, formatted as Prettier formats CSS: its own
 * settings in a :root rule, and each object in it as a rule of its own, named by its key, with camelCase keys as
 * kebab-case properties. An object inside a rule is a nested rule.
 *
 * .. code-block:: text
 *
 *     {"googleFont": "Inter", "conversationHeader": {"backgroundColor": "#231f20"}}
 *     :root {
 *       google-font: "Inter";
 *     }
 *
 *     .conversation-header {
 *       background-color: #231f20;
 *     }
 */
export function styleObjectAsCss(styles: Record<string, unknown>): string {
  const isObject = (value: unknown): value is Record<string, unknown> =>
    typeof value === "object" && value !== null && !Array.isArray(value);
  const rule = (selector: string, body: Record<string, unknown>, indent: string): string => {
    const lines: string[] = [];
    for (const [key, value] of Object.entries(body)) {
      if (isObject(value)) {
        if (lines.length) lines.push("");
        lines.push(rule(`.${kebabCase(key)}`, value, `${indent}  `));
      } else if (value !== null && value !== undefined && value !== "") {
        lines.push(`${indent}  ${kebabCase(key)}: ${cssValue(key, value)};`);
      }
    }
    return [`${indent}${selector} {`, ...lines, `${indent}}`].join("\n");
  };
  const own = Object.fromEntries(Object.entries(styles).filter(([, value]) => !isObject(value)));
  const groups = Object.entries(styles).filter((entry): entry is [string, Record<string, unknown>] =>
    isObject(entry[1]),
  );
  const rules = Object.keys(own).length ? [rule(":root", own, "")] : [];
  rules.push(...groups.map(([key, value]) => rule(`.${kebabCase(key)}`, value, "")));
  return `${rules.join("\n\n")}\n`;
}

/** Whether a value is missing: null, undefined, an empty string, or an empty list. */
function isEmpty(value: unknown): boolean {
  return value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
}

/** A value as text, for the types that show text. */
function asText(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

/** The muted dash of a field that has no value. */
export function NoValue() {
  return (
    <span className="smarter-detail-empty" title={gettext("No value")}>
      —<span className="visually-hidden">{gettext("No value")}</span>
    </span>
  );
}

/** A value, formatted by its type. */
export function DetailValue({
  value,
  type = "text",
  tone = "success",
}: {
  value: unknown;
  type?: DetailValueType;
  tone?: DetailTone;
}) {
  if (type === "bool") {
    // a boolean is never "empty": false is a value.
    if (value === null || value === undefined) return <NoValue />;
    // a dot and a word, rather than a badge: a section of flags stays quiet, and a "yes" stands out.
    return (
      <span className={`smarter-detail-bool smarter-detail-bool-${value ? `yes smarter-detail-tone-${tone}` : "no"}`}>
        <span className="smarter-detail-bool-dot" aria-hidden="true" />
        {value ? gettext("Yes") : gettext("No")}
      </span>
    );
  }
  if (isEmpty(value)) return <NoValue />;
  switch (type) {
    case "dateTime": {
      const text = asText(value);
      return (
        <time dateTime={text} title={text}>
          {formatDateTime(text, "date")}
          {/* how long ago, from now: the epoch, as the reference, is never within seconds of the date. */}
          <span className="smarter-detail-secondary ms-2">{formatDateTime(text, "relative", EPOCH)}</span>
        </time>
      );
    }
    case "url": {
      const href = asText(value);
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="smarter-detail-link text-break">
          {href}
          <i className="ki-outline ki-exit-right-corner fs-7 ms-1" aria-hidden="true" />
        </a>
      );
    }
    case "number":
      return <span className="smarter-detail-number">{Number(value).toLocaleString()}</span>;
    case "code":
      return <code className="smarter-detail-code">{asText(value)}</code>;
    case "json": {
      let json: string;
      if (typeof value === "string") {
        try {
          json = prettyJson(JSON.parse(value));
        } catch {
          return <CodeBlock lines={plainLines(value)} label="JSON" className={CODE_FIELD} />;
        }
      } else {
        json = prettyJson(value);
      }
      return <CodeBlock lines={highlightJson(json)} label="JSON" className={CODE_FIELD} />;
    }
    case "yaml":
      return <CodeBlock lines={highlightYaml(asYaml(value))} label="YAML" className={CODE_FIELD} />;
    case "css": {
      let styles: unknown = value;
      if (typeof value === "string") {
        try {
          styles = JSON.parse(value);
        } catch {
          return <CodeBlock lines={plainLines(value)} label="CSS" className={CODE_FIELD} />;
        }
      }
      if (typeof styles !== "object" || styles === null || Array.isArray(styles)) {
        return <CodeBlock lines={plainLines(asText(value))} label="CSS" className={CODE_FIELD} />;
      }
      const css = styleObjectAsCss(styles as Record<string, unknown>);
      return <CodeBlock lines={highlightCss(css)} label="CSS" className={CODE_FIELD} />;
    }
    case "sql":
      return <CodeBlock lines={highlightSql(asText(value))} label="SQL" className={CODE_FIELD} />;
    case "source":
      return <CodeBlock lines={plainLines(asText(value))} label={gettext("Code")} className={CODE_FIELD} />;
    case "list": {
      const items = Array.isArray(value) ? value : [value];
      return (
        <ul className="smarter-detail-list">
          {items.map((item, index) => (
            <li key={index} className="badge badge-light text-gray-800 fw-semibold">
              {asText(item)}
            </li>
          ))}
        </ul>
      );
    }
    default:
      return <span className="text-break">{asText(value)}</span>;
  }
}

export interface DetailFieldProps {
  /** The field's label, e.g. "Created". */
  label: string;
  /** The value, formatted by type. Ignored when the field has children. */
  value?: unknown;
  /** How to format the value. Defaults to text. */
  type?: DetailValueType;
  /** The color of a bool's "yes": success by default, warning or danger for a flag that warns. */
  tone?: DetailTone;
  /** A short explanation of the field, shown by an icon beside its label. */
  help?: string;
  /** Whether the field spans the whole width of its section, e.g. for a long text or a list. */
  wide?: boolean;
  /** The value, when it needs its own markup, e.g. chips. */
  children?: ReactNode;
}

/** One labeled value of a DetailSection. */
export function DetailField({ label, value, type, tone, help, wide = false, children }: DetailFieldProps) {
  return (
    <div className={`smarter-detail-field${wide ? " smarter-detail-field-wide" : ""}`}>
      <dt>
        {label}
        {help && (
          <span className="smarter-detail-help" title={help}>
            <i className="ki-outline ki-information-5 fs-7" aria-hidden="true" />
            <span className="visually-hidden">{help}</span>
          </span>
        )}
      </dt>
      <dd>{children ?? <DetailValue value={value} type={type} tone={tone} />}</dd>
    </div>
  );
}

export interface DetailSectionProps {
  /** The section's title, e.g. "Detection". */
  title: string;
  /** A Keen icon's name, without its ki- prefix, e.g. "setting-2". */
  icon?: string;
  /** Its fields. */
  children: ReactNode;
}

/** A titled card of fields. */
export function DetailSection({ title, icon, children }: DetailSectionProps) {
  return (
    <section className="smarter-detail-section">
      <h3 className="smarter-detail-section-title">
        {icon && (
          <span className="smarter-detail-section-icon" aria-hidden="true">
            <i className={`ki-outline ki-${icon}`} />
          </span>
        )}
        {title}
      </h3>
      <dl className="smarter-detail-grid">{children}</dl>
    </section>
  );
}

export interface DetailOverviewProps {
  /** The resource's description. */
  description?: string | null;
  /** What sits beside it: the resource's status, and its actions. */
  children?: ReactNode;
}

/** The top of a Details tab: the resource's description, beside its status and actions. */
export function DetailOverview({ description, children }: DetailOverviewProps) {
  return (
    <div className="smarter-detail-overview">
      <p className={`smarter-detail-description${description ? "" : " text-gray-500 fst-italic"}`}>
        {description || gettext("No description.")}
      </p>
      {children && <div className="smarter-detail-overview-aside">{children}</div>}
    </div>
  );
}

/** The fields that every resource has, of which a list's object has some or all. */
export interface ResourceMetadata {
  id?: number | string | null;
  hashedId?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  version?: string | null;
  tags?: Tags;
  annotations?: Annotations;
  userProfile?: UserProfile | null;
}

export interface ResourceMetadataSectionProps {
  resource: ResourceMetadata;
  /** Narrows the list by a tag or annotation that is clicked. */
  filtering?: Filtering;
  /** More fields, after the common ones. */
  children?: ReactNode;
}

/** The section of the fields that every resource has: its owner, account, version, identifiers, dates, tags and annotations. */
export function ResourceMetadataSection({ resource, filtering, children }: ResourceMetadataSectionProps) {
  const user = resource.userProfile?.user;
  return (
    <DetailSection title={gettext("Metadata")} icon="information-2">
      <DetailField label={gettext("Owner")} value={user?.username} />
      <DetailField label={gettext("Owner email")} value={user?.email} />
      <DetailField label={gettext("Account")} value={resource.userProfile?.account?.accountNumber} type="code" />
      <DetailField label={gettext("Version")} value={resource.version} type="code" />
      <DetailField label={gettext("Created")} value={resource.createdAt} type="dateTime" />
      <DetailField label={gettext("Last updated")} value={resource.updatedAt} type="dateTime" />
      {/* a list whose serializer doesn't send an identifier leaves it out, rather than show it empty. */}
      {resource.id !== undefined && <DetailField label={gettext("ID")} value={resource.id} type="code" />}
      {resource.hashedId !== undefined && (
        <DetailField label={gettext("Hashed ID")} value={resource.hashedId} type="code" />
      )}
      {children}
      <DetailField label={gettext("Tags")} wide>
        <TagChips tags={resource.tags} filtering={filtering} />
      </DetailField>
      <DetailField label={gettext("Annotations")} wide>
        <AnnotationChips annotations={resource.annotations} filtering={filtering} />
      </DetailField>
    </DetailSection>
  );
}
