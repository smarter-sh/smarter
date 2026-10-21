---
name: smarter-chat-embed
description: Use when changing Smarter Chat's embed script (smarter/react/packages/smarter.sh-chat/src/embed/, dist/embed.js) - the <smarter-chat> custom element, its shadow root and css, the launcher, the options read from attributes, data- attributes and window.SmarterChatConfig, window.SmarterChat, the embed builds in vite.config.ts, the lazily loaded Mermaid and KaTeX fonts, the size budget, or when adding an embed option and carrying it to the platform integrations (WordPress, Drupal, Shopify, Google Tag Manager, Docusaurus/MkDocs/Sphinx/VitePress) and the docs.
---

# Smarter Chat: the Embed Script

`dist/embed.js` is one classic script with React and the chat included, which
renders `<smarter-chat>` elements in shadow roots. Paths are relative to
`smarter/react/packages/smarter.sh-chat`. Decisions:
`doc/adr/006-embed-script.md`, `007-distribution.md`, `010-bundle-size.md`.

## Files

| File (in `src/embed/`)           | Responsibility                                                                                            |
| -------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `index.ts`                       | Entry. Captures its own url, defines the element, sets `window.SmarterChat`, runs `autoMount()`           |
| `options.ts`                     | **The one definition of the options**: `EmbedOptions`, `OPTION_ATTRIBUTES`, defaults, `parseOptions()`    |
| `element.ts`                     | `SmarterChatElement`: shadow root, css, render on attribute change, `open/close/toggle`, the toggle event |
| `EmbedApp.tsx`                   | Inline chat, or launcher (button + panel); passes options to `SmarterChat` as props                       |
| `autoMount.ts`                   | The script tag's `data-` attributes and `window.SmarterChatConfig` to elements, once per chatbot          |
| `css.ts`                         | Collects the build's css strings; applies them to each shadow root; hoists `@font-face` to the page       |
| `assets.ts`                      | The url of `embed/` beside the script, or jsDelivr's copy of the same version                             |
| `mermaidImport.ts`, `mermaid.ts` | The separate Mermaid build, imported on the first diagram                                                 |
| `styles.css`                     | The launcher's and inline wrapper's css                                                                   |

In `vite.config.ts`: `embedConfig()` (IIFE, `process.env.NODE_ENV` defined as
production, plugins `embedCss` and `embedMermaidImport`) and
`embedMermaidConfig()` (ES module with chunks in `dist/embed/mermaid/`).
`build:embed` runs both, after `build:lib`, into the same `dist/`
(`emptyOutDir: false`). Build order matters: `build:lib` empties `dist/`.

`window.SmarterChat.version` is `package.json`'s version when the script is
built. `uiChatRelease.yml` sets it to the platform's release version before it
builds, and `check:dist` verifies it.

## Adding an option

1. `options.ts`: the field in `EmbedOptions` with a doc comment, its
   kebab-case name in `OPTION_ATTRIBUTES` (which is also the element's
   `observedAttributes`), and its parsing in `parseOptions()`, **validated**,
   with a default for invalid values (`safeCssValue()`, `booleanOption()`, a
   fixed set, a pattern). Never pass a page's string through unchecked.
2. `EmbedApp.tsx`: use it, usually as a `SmarterChat` prop. If the chat lacks
   that prop, add it first (`smarter-chat-development`).
3. Tests in `options.test.ts` (default, valid, invalid, hostile), and in
   `element.test.ts` or `autoMount.test.ts` if it changes behavior.
   `window.SmarterChatConfig`'s camelCase name is derived by `kebabCase()`;
   test one config object that sets it.
4. Docs: the Options table in `README.md`, and
   `docs/source/smarter-framework/smarter-chat/embedding.rst`.
5. In `smarter/react`: `npm run build -w @smarter.sh/ui-chat && npm run check:dist -w @smarter.sh/ui-chat`.
6. It's a `feat(embed)`. Renaming or removing an option is breaking
   (`doc/adr/014-versioning.md`).

## Carrying a release to the integrations

The integrations are separate repositories, beside this one. They write the
tag and pin an exact version of `@smarter.sh/ui-chat`, which they bump in their
own `monthly-maintenance`. The package's version is the platform's (0.36.0 and
later), not its old 0.16 line:

| Repository                        | Pin                                                                                       | Setting names   |
| --------------------------------- | ----------------------------------------------------------------------------------------- | --------------- |
| `../smarter-wordpress`            | `SMARTER_CHAT_EMBED_VERSION` in `smarter-chat/smarter-chat.php`, vendored by `make embed` | snake_case      |
| `../smarter-drupal`               | `EmbedConfig::EMBED_VERSION`, and `smarter_chat.libraries.yml`                            | snake_case      |
| `../smarter-shopify`              | `snippets/smarter-chat-script-url.liquid`                                                 | block settings  |
| `../smarter-gtm-template`         | a minor range in `template.tpl`                                                           | template fields |
| `../smarter-docs-site-generators` | `embed.json` (`make embed-version V=x.y.z`)                                               | per generator   |

Don't change those repositories as part of a change here unless the user asks;
say in your summary which ones a new option should reach. Each one's
`smarter-<name>-development` skill has its own "adding an option" steps. To
test an unreleased embed script there, build here and point the integration at
this package's `dist/` (e.g. WordPress's
`make embed EMBED_SOURCE=../smarter/smarter/react/packages/smarter.sh-chat/dist`),
or install an `alpha` version from npm, which each platform prerelease
publishes.

## Traps

- **`document.currentScript` is only set while the script first runs.**
  `index.ts` captures it at load; code that runs later must use `assetUrl()`.
- **Every css import becomes shadow-root css** in this build. A component that
  expects page-level css (e.g. a portal into `document.body`) won't be styled.
  Render inside the element.
- **`@font-face` doesn't work inside a shadow root**: fonts are hoisted to the
  page's head, once (`FONT_STYLE_ID`). The LLMClient's Google font link goes
  to the page's head too (`src/lib/styles.ts`).
- **Running twice adds nothing**: `mountChat()` skips a chatbot that already has
  an element marked `data-smarter-chat-auto`. Keep that for single-page apps
  and tag managers.
- **The launcher renders the chat only on first open**, then keeps it mounted
  but hidden. Don't fetch on page load.
- **Size**: `check:dist` fails above 400 kB gzipped (about 290 kB today). A new
  dependency imported by the chat lands in `embed.js`; large, rare ones must
  be lazy, like Mermaid.
- **React's production build is required**: `check:dist` fails if
  `process.env.NODE_ENV` survives, which a web page can't resolve.
- **jsDelivr's ranges** (`@0`, `@0.36`) follow only `latest` releases from main;
  `uiChatRelease.yml` refreshes them after each one. Prereleases are only on
  the `alpha` and `beta` dist-tags.
- The launcher's panel is a region, not a dialog: no focus trap; Escape closes
  it and returns focus to the button (`doc/adr/011-accessibility.md`).
