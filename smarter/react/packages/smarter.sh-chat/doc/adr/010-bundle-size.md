# ADR-010: Bundle Size and Lazy Loading

## Status

Accepted

## Context

The chat renders math (KaTeX, with about 60 font files) and diagrams (Mermaid, about 1.2 MB gzipped). Most messages have neither, and most visitors of a page with a launcher never open it. The embed script includes React (ADR-006), and is loaded by every page of a site.

## Decision

- **Mermaid is loaded only when a message first has a diagram.** The library leaves it external, for the page's bundler to split into chunks; the app puts it outside its vendor chunk; the embed script imports a separate ES module build, `dist/embed/mermaid/mermaid.js`, beside `embed.js` (a classic script can `import()` a module, but can't be split).
- **KaTeX's fonts are downloaded only when an equation uses them.** The library leaves KaTeX's css out of `ui-chat.css`, and its users import `katex/dist/katex.min.css` themselves; the embed script refers to woff2 fonts in `dist/embed/katex/fonts/`, rather than inlining them.
- **The launcher renders the chat only when it is first opened**, so a page view that never opens it makes no request to the platform.
- **The embed script has a size budget**: 400 kB gzipped, checked by `scripts/check-dist.mjs` on every build. It is about 330 kB today. It is React's production build, minified, with a source map.
- React is a peer dependency of the library, never bundled into it.

## Alternatives Considered

- **Inline everything.** KaTeX's fonts alone would add 1.5 MB to every page; Mermaid would triple the script.
- **Preact instead of React** in the embed script. chatscope and the chat's other dependencies target React, and the workbench, the library and the embed script would no longer run the same code.
- **No budget.** Size grows one dependency at a time, and nobody notices until a site owner does.

## Consequences

- **Positive:**
  - A page with a closed launcher costs one cached script and no requests to the platform.
- **Negative:**
  - The first diagram, or the first equation, waits for a download.
  - `embed.js` and `embed/` must be copied together by sites that host them.
  - A new dependency must fit the budget, or be loaded lazily too.

## Related ADRs

- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-013: CI/CD and Releases](013-ci-cd.md)
