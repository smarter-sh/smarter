# ADR-002: One Source, Three Builds

## Status

Accepted

Amended by [ADR-019](019-hosted-by-the-workbench.md): the app build moved to the platform, as its `@smarter/workbench` app, which imports the library. `npm run build` builds the library and the embed script.

## Context

Smarter Chat has three kinds of consumers:

- the Smarter web console, whose pages are React apps that Django hosts, built by Vite into Django's static files with a `manifest.json` (platform [ADR-019](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/019-react.rst)),
- React applications, which install an npm package and bundle it with their own React,
- every other web page: WordPress, Drupal, Shopify, Google Tag Manager, documentation sites and plain html, which have no bundler and no React 19.

## Decision

One `src/`, and one `vite.config.ts`, with a mode per build:

| Build            | Command                                                      | Entry                | Output                                                                                    |
| ---------------- | ------------------------------------------------------------ | -------------------- | ----------------------------------------------------------------------------------------- |
| The app          | `npm run build`                                              | `src/main.tsx`       | Django's static directory inside the platform's workspace, else `build/`, with a manifest |
| The library      | `npm run build:lib` (`--mode lib`)                           | `src/index.ts`       | `dist/`: ES and UMD bundles, `ui-chat.css`, type declarations. React and Mermaid external |
| The embed script | `npm run build:embed` (`--mode embed`, then `embed-mermaid`) | `src/embed/index.ts` | `dist/embed.js`, a classic script with React included, and `dist/embed/` (ADR-006)        |

React is a peer dependency of the library (`react` and `react-dom` 19), so that a React application has one React. The app reads its props from its root element's `smarter-*` attributes (`src/main.tsx`), as every console app does. The library's public api is `src/index.ts` (ADR-014).

Two modules are swapped between builds, never forked: `src/lib/mermaidImport.ts` becomes `src/embed/mermaidImport.ts` in the embed build, and css imports become strings for a shadow root (ADR-006). Everything else is the same code.

## Alternatives Considered

- **Separate packages for the library and the embed script.** Two versions to release and keep in step, for one source.
- **Only the library, with a snippet for non-React sites.** A site without a bundler can't load an ES module that imports `react`.
- **An iframe that the platform hosts.** The platform has no such page, an iframe can't float a launcher over the site, and it couldn't follow the visitor's chat session across pages without third-party cookies.

## Consequences

- **Positive:**
  - A fix reaches the workbench, React sites and embedded sites in one release.
  - `make build` builds all three, and `scripts/check-dist.mjs` checks the published two (ADR-013).
- **Negative:**
  - `vite.config.ts` is long, with Vite plugins whose purpose isn't obvious; each has a comment that says why.
  - A change must work in all three: e.g. a new css file is shadow-root css in the embed script, and page css in the library.

## Related ADRs

- [ADR-003: Its Own Repository, Inside the Platform's Workspace](003-repository.md)
- [ADR-006: The Embed Script](006-embed-script.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
