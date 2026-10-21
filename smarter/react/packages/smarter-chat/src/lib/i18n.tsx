/**
 * Translation functions for Smarter Chat.
 *
 * Smarter Chat is translated with gettext, the same way as the Smarter web console, and has the same
 * languages: English, which is the source language of every message, Spanish (Latin American, under the
 * generic "es" code), French and Brazilian Portuguese ("pt-br", whose catalog is pt_BR). Its message catalogs are its own, in locale/<language>/LC_MESSAGES/smarter-chat.po,
 * because the chat also runs on pages that the Smarter platform didn't render: the npm library's and the embed
 * script's. `npm run i18n` compiles them into src/catalogs.gen.ts, which every build bundles.
 *
 * The language is the one that SmarterChat's `language` prop asks for, or else the page's, from the lang attribute
 * of its <html> element, which the web console sets to the console's language, or else the browser's. A language
 * that Smarter Chat doesn't have falls back to its generic language (fr-CA to fr), or else to a regional language
 * of the same generic language (pt and pt-PT to pt-br), and then to English.
 * SmarterChat activates its language as it renders, so that the functions here, which every component and module
 * calls, translate into it. A page with two chats in two languages therefore gets the language of the last one to
 * render.
 *
 * Every message is English source text, and must be a string literal, so that `npm run i18n` can extract it.
 * Interpolate values afterwards, with Python-style named placeholders, so that a translator can move them:
 *
 * @example
 *   gettext("Start a new chat");
 *   interpolate(gettext("%(assistant)s is typing"), { assistant });
 *   interpolate(ngettext("%(count)s tool", "%(count)s tools", n), { count: n });
 *   pgettext("button", "Code");
 *   // a React element inside a sentence:
 *   interpolateNodes(gettext("Delete %(name)s?"), { name: <strong>{name}</strong> });
 *
 * A comment that begins with "Translators:" on the line before a call is copied into the message catalogs, for the
 * translator. Translate when the text is displayed, never in a module-level constant, which is evaluated once,
 * before any language is activated.
 */
import { Fragment, type ReactNode } from "react";

import { CATALOGS, type Catalog } from "@/catalogs.gen";

/** The source language, which has no catalog. */
export const DEFAULT_LANGUAGE = "en";

/** A language tag or locale name as a lowercase language tag, e.g. "pt-br" for "pt_BR" or " PT-BR ". */
const normalize = (tag: string) => tag.trim().toLowerCase().replaceAll("_", "-");

/** The catalogs by language tag: a catalog is named after its locale name, e.g. pt_BR for pt-br. */
const CATALOGS_BY_LANGUAGE: Record<string, Catalog> = Object.fromEntries(
  Object.entries(CATALOGS).map(([language, catalog]) => [normalize(language), catalog]),
);

/** The languages that Smarter Chat is translated into, including English, as lowercase language tags. */
export const LANGUAGES: readonly string[] = [DEFAULT_LANGUAGE, ...Object.keys(CATALOGS_BY_LANGUAGE)];

type InterpolationValues = Record<string, string | number | null | undefined>;

const PLACEHOLDER = /%\(([A-Za-z_][A-Za-z0-9_]*)\)s/g;
// gettext's separator of a message's context and its msgid.
const CONTEXT_SEPARATOR = "\u0004";

let activeLanguage: string | null = null;

/**
 * The language of Smarter Chat that best matches a language tag, e.g. "fr" for "fr-CA", or "pt-br" for "pt" and
 * "pt-PT", or null if it has none. The tag is case-insensitive, and may use "_" for "-", as Django's locale names do.
 */
export function matchLanguage(tag: string | null | undefined): string | null {
  const normalized = tag ? normalize(tag) : "";
  if (!normalized) return null;
  if (LANGUAGES.includes(normalized)) return normalized;
  const generic = normalized.split("-")[0];
  if (LANGUAGES.includes(generic)) return generic;
  return LANGUAGES.find((language) => language.split("-")[0] === generic) ?? null;
}

/**
 * The language to display: the requested one, if Smarter Chat has it, or else the page's (<html lang>), or else
 * the browser's first one that it has, or else English.
 */
export function resolveLanguage(requested?: string | null): string {
  const candidates: (string | null | undefined)[] = [requested];
  if (typeof document !== "undefined") candidates.push(document.documentElement.lang);
  if (typeof navigator !== "undefined") candidates.push(...(navigator.languages ?? [navigator.language]));
  for (const candidate of candidates) {
    const language = matchLanguage(candidate);
    if (language) return language;
  }
  return DEFAULT_LANGUAGE;
}

/** Translates from now on into the language that resolveLanguage() chooses for the request, and returns it. */
export function activateLanguage(requested?: string | null): string {
  activeLanguage = resolveLanguage(requested);
  return activeLanguage;
}

/** The active language. Until one is activated, the page's or the browser's. */
export function currentLanguage(): string {
  activeLanguage ??= resolveLanguage();
  return activeLanguage;
}

const catalog = (): Catalog | undefined => CATALOGS_BY_LANGUAGE[currentLanguage()];

/** The translation of a message, by its key, or undefined if it has none. */
function lookup(key: string): Catalog["messages"][string] | undefined {
  const translation = catalog()?.messages[key];
  return translation === "" ? undefined : translation;
}

/** The plural form of a translated message, for a count, or the English one if it has no translation. */
function plural(key: string, singular: string, pluralText: string, count: number): string {
  const translation = lookup(key);
  const active = catalog();
  if (Array.isArray(translation) && active) {
    return translation[active.plural(count)] || (count === 1 ? singular : pluralText);
  }
  return count === 1 ? singular : pluralText;
}

/** Translates a message. */
export function gettext(msgid: string): string {
  const translation = lookup(msgid);
  return typeof translation === "string" ? translation : msgid;
}

/** Translates a message that has a singular and a plural form, chosen by count. */
export function ngettext(singular: string, pluralText: string, count: number): string {
  return plural(singular, singular, pluralText, count);
}

/** Translates a message in a context, which tells apart two messages with the same English text. */
export function pgettext(context: string, msgid: string): string {
  const translation = lookup(`${context}${CONTEXT_SEPARATOR}${msgid}`);
  return typeof translation === "string" ? translation : msgid;
}

/** ngettext() in a context. */
export function npgettext(context: string, singular: string, pluralText: string, count: number): string {
  return plural(`${context}${CONTEXT_SEPARATOR}${singular}`, singular, pluralText, count);
}

/**
 * Replaces each %(name)s placeholder in a translated message with values[name].
 * A placeholder with no value is left as it is, so that the mistake shows.
 */
export function interpolate(message: string, values: InterpolationValues): string {
  return message.replace(PLACEHOLDER, (placeholder, name: string) => {
    const value = values[name];
    return value === undefined || value === null ? placeholder : String(value);
  });
}

/**
 * interpolate() for values that are React nodes, e.g. a name in <strong> inside a sentence. Returns a fragment of
 * the message's text and the values, in the order that the (translated) message puts them.
 */
export function interpolateNodes(message: string, values: Record<string, ReactNode>): ReactNode {
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of message.matchAll(PLACEHOLDER)) {
    const [placeholder, name] = match;
    const index = match.index ?? 0;
    if (index > last) parts.push(message.slice(last, index));
    parts.push(name in values ? values[name] : placeholder);
    last = index + placeholder.length;
  }
  if (last < message.length) parts.push(message.slice(last));
  return (
    <>
      {parts.map((part, index) => (
        <Fragment key={index}>{part}</Fragment>
      ))}
    </>
  );
}
