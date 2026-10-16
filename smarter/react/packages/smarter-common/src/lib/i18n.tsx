/**
 * Translation functions for the web console's React apps.
 *
 * The web console is translated with gettext. Django renders each page in the
 * user's language, and dashboard/base.html loads that language's message
 * catalog for the React apps from Django's JavaScriptCatalog view (the djangojs
 * domain), which defines window.django.gettext() and friends. These functions
 * call it, and fall back to the English source text when no catalog is loaded,
 * e.g. in tests and Storybook.
 *
 * Every message is English source text, and must be a string literal, so that
 * `npm run i18n:extract` can find it. Interpolate values afterwards, with
 * Python-style named placeholders, so that a translator can move them:
 *
 * @example
 *   gettext("Secrets");
 *   interpolate(gettext("Rename secret %(name)s."), { name: secret.name });
 *   ngettext("%(count)s secret", "%(count)s secrets", n);
 *   pgettext("verb", "Clone");
 *   // a React element inside a sentence:
 *   interpolateNodes(gettext("Delete secret %(name)s?"), { name: <strong>{secret.name}</strong> });
 *
 * A comment that begins with "Translators:" on the line before a call is copied
 * into the message catalog for the translator.
 */
import { Fragment, type ReactNode } from "react";

/** The functions that Django's JavaScriptCatalog defines on window.django. */
export interface DjangoCatalog {
  gettext: (msgid: string) => string;
  ngettext: (singular: string, plural: string, count: number) => string;
  pgettext: (context: string, msgid: string) => string;
  npgettext: (context: string, singular: string, plural: string, count: number) => string;
}

declare global {
  interface Window {
    django?: Partial<DjangoCatalog>;
  }
}

type InterpolationValues = Record<string, string | number | null | undefined>;

const PLACEHOLDER = /%\(([A-Za-z_][A-Za-z0-9_]*)\)s/g;

const catalog = (): Partial<DjangoCatalog> | undefined => (typeof window === "undefined" ? undefined : window.django);

/** Translates a message. */
export function gettext(msgid: string): string {
  const django = catalog();
  return django?.gettext ? django.gettext(msgid) : msgid;
}

/** Translates a message that has a singular and a plural form, chosen by count. */
export function ngettext(singular: string, plural: string, count: number): string {
  const django = catalog();
  if (django?.ngettext) return django.ngettext(singular, plural, count);
  return count === 1 ? singular : plural;
}

/** Translates a message in a context, which tells apart two messages with the same English text. */
export function pgettext(context: string, msgid: string): string {
  const django = catalog();
  return django?.pgettext ? django.pgettext(context, msgid) : msgid;
}

/** ngettext() in a context. */
export function npgettext(context: string, singular: string, plural: string, count: number): string {
  const django = catalog();
  if (django?.npgettext) return django.npgettext(context, singular, plural, count);
  return count === 1 ? singular : plural;
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
 * interpolate() for values that are React nodes, e.g. a name in <strong> inside a
 * sentence. Returns a fragment of the message's text and the values, in the order
 * that the (translated) message puts them.
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

/** The language of the page, from the lang attribute that Django renders on <html>, e.g. "en". */
export function currentLanguage(): string {
  if (typeof document === "undefined") return "en";
  return document.documentElement.lang || "en";
}
