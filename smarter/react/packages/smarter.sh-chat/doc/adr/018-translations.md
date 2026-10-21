# ADR-018: Translations

## Status

Accepted

Follows the platform's translations: gettext, English source text, and the same languages as the web console.

## Context

The Smarter web console is translated with gettext into Spanish (Latin American, under the generic `es` code) and
French. Its React apps call `gettext()` from `@smarter/common`, which reads the catalog that Django's `/jsi18n/` view
loads into the page. Smarter Chat is the console's prompt workbench too, so it must speak the console's language. But
it also runs where Django rendered nothing: in other React applications, from the npm package, and on any website,
from the embed script ([ADR-002](002-three-builds.md)). There is no `/jsi18n/` there, and the page's language is the
website's.

## Decision

- **The same api and rules as the console.** `gettext`, `ngettext`, `pgettext`, `npgettext`, `interpolate` and
  `interpolateNodes` in `src/lib/i18n.tsx`, with English messages as string literals, `%(name)s` placeholders, whole
  sentences, and `Translators:` comments.
- **Its own catalogs, bundled.** `locale/<language>/LC_MESSAGES/smarter-chat.po`, in gettext's format, for the same
  translators and tools as the console's. `scripts/i18n.mjs` (`npm run i18n`) extracts the messages with the
  TypeScript compiler, as the console's `extract.ts` does, merges them into the `.po` files, and compiles those into
  `src/catalogs.gen.ts`, which every build includes. The `.po` files' plural rules are compiled into code then,
  so nothing is evaluated at runtime, and a page's Content Security Policy doesn't need `unsafe-eval`.
- **The language:** the `language` prop (the embed script's `language` option), or else the page's
  `<html lang>`, which the web console sets to the console's language, or else the browser's. A regional variant gets
  its generic language (`es-MX` to `es`), and any other language gets English. `SmarterChat` activates it as it
  renders.
- **What is translated:** the chat's own text, its labels, and the errors that it displays. Not the LLMClient's own
  text (its name, welcome message, example prompts and placeholder), which its manifest sets, not the conversation,
  not the platform's progress messages and errors.

## Alternatives Considered

- **Django's catalog, in the workbench only.** The console's `djangojs` catalog could carry the chat's messages. The
  npm package and the embed script would still need their own, so there would be two pipelines for the same messages.
- **Loading the catalogs from the platform.** Another request before the chat can render, from a platform that may be
  an older version, and a CORS dependency for every embedding website.
- **A JavaScript i18n library** (i18next, FormatJS). Another message format than the console's, more bytes, and
  another tool for its translators.
- **Parsing the `.po` files at runtime.** Their comments and references would add bytes to `embed.js`, and their
  plural rules would need `new Function()`.

## Consequences

- **Positive:**
  - The workbench follows the console's language with no change on the platform, and a website's chat follows the
    website's language.
  - Translators work with one format, and the two projects' translations use the same terms.
  - `src/catalogs.test.ts` fails when a catalog is out of date, or a message isn't translated.
- **Negative:**
  - Every language adds its messages to `embed.js`: a few kB gzipped each ([ADR-010](010-bundle-size.md)).
  - The active language is global, as gettext's is: two chats in two languages on one page get the language of the
    last one to render.
  - A new message needs its translations before the tests pass.

## Related ADRs

- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-010: Bundle Size and Lazy Loading](010-bundle-size.md)
- [ADR-011: Accessibility](011-accessibility.md)
