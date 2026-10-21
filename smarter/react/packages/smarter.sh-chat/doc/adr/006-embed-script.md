# ADR-006: The Embed Script

## Status

Accepted

## Context

Most websites that want a Smarter chat aren't React applications. WordPress bundles its own React, only in wp-admin; Shopify themes, Google Tag Manager and documentation sites can add a script tag, and little else. Themes and other scripts bring css that would restyle the chat, and the chat's css must not restyle the site. Each platform integration (WordPress, Drupal, Shopify, Google Tag Manager, Docusaurus, MkDocs, Sphinx, VitePress) would otherwise build its own chat.

## Decision

`dist/embed.js` (`src/embed/`) is one **classic script** (an IIFE), with React, React DOM, the chat and its css included. Running it:

1. remembers its own url, to find its other files in `embed/` beside it (`assets.ts`), or on jsDelivr at the same version if it has none,
2. defines the **`<smarter-chat>` custom element** (`element.ts`), which renders `EmbedApp` in its own **open shadow root**, with the chat's css applied there (a constructable stylesheet, else a style element), so that the page's css and the chat's can't touch each other,
3. adds a launcher for its script tag's `data-chatbot`, and for each object of `window.SmarterChatConfig` (`autoMount.ts`), once per chatbot, so a script that runs twice adds nothing,
4. sets `window.SmarterChat` (`version`, `open`, `close`, `toggle`, `mount`).

Options have **one definition** (`options.ts`) and three spellings: the element's attributes and the script tag's `data-` attributes in kebab-case, and `window.SmarterChatConfig`'s properties in camelCase. Only `chatbot` is required; every other value is validated, and replaced by its default if it isn't valid. The element is `inline` by default, and the script tag's is a `launcher`. The launcher renders the chat only when first opened, and keeps it rendered when closed. Pages can style the launcher with `::part(launcher)`, `::part(panel)` and `::part(chat)`.

Fonts are the exception to the shadow root: browsers ignore `@font-face` in one, so `@font-face` rules are added to the page's head once, under the chat's own font names. Mermaid and KaTeX's fonts are separate files (ADR-010).

The platform integrations are thin: they write the tag, or `window.SmarterChatConfig`, with their own settings screens, and pin a version (ADR-007). A feature that an integration needs goes into the embed script first.

## Alternatives Considered

- **Each integration bundles the library itself.** Eight builds of React and the chat, each with its own bugs.
- **An ES module.** Tag managers, and many CMSs, can only add classic scripts, and a module can't read `document.currentScript`.
- **No shadow DOM, with prefixed class names only.** A theme's element selectors (`button`, `p`, `a`) would still restyle the chat.
- **An iframe.** See ADR-002.

## Consequences

- **Positive:**
  - Every non-React site adds a chat the same way, with one tag.
  - The embed script's options are the integrations' settings, with the same names.
- **Negative:**
  - The script includes React, about 330 kB gzipped (ADR-010), even on a page that has React.
  - An option is public api: renaming or removing one breaks the integrations and every hand-written tag (ADR-014).

## Related ADRs

- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-007: Distribution: npm and jsDelivr](007-distribution.md)
- [ADR-010: Bundle Size and Lazy Loading](010-bundle-size.md)
- [ADR-011: Accessibility](011-accessibility.md)
