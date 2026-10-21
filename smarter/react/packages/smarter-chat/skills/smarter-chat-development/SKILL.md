---
name: smarter-chat-development
description: Start here for any change to the smarter-chat repository, Smarter Chat (the @smarter.sh/ui-chat npm package), the React chat UI of Smarter LLMClients, which is built two ways from one source - the npm library, which the web console's prompt workbench imports, and the embed script for any web page. Gives the rules, the architecture, the two clones (standalone and inside the platform's React workspace), how a change crosses into ../smarter (the api contract, the workbench that hosts the chat, the docs), the common changes, and an index of the narrower skills.
---

# Smarter Chat: Development

Smarter Chat is the front end of a deployed Smarter LLMClient, and of nothing
else (`doc/adr/001-scope.md`). It never calls an LLM provider. One `src/`
builds two things (`doc/adr/002-three-builds.md`, amended by `doc/adr/019-hosted-by-the-workbench.md`), which
`npm run build` runs one after the other:

| Build            | Command               | Entry                | Consumer                                                            |
| ---------------- | --------------------- | -------------------- | ------------------------------------------------------------------- |
| The library      | `npm run build:lib`   | `src/index.ts`       | React applications (`npm install`), and the web console's workbench |
| The embed script | `npm run build:embed` | `src/embed/index.ts` | Every other web page, and the platform plugins                      |

The web console's Prompt Engineer's Workbench is the platform's own app,
`@smarter/workbench` (`../smarter/smarter/react/packages/smarter-workbench`), which imports the library and puts
its developer Console beside the chat, with the props for a hosting page (`verbose`, `reloadKey`,
`headerActions`, `onConfig`, `onNewChat`, `onModeChange`). `npm run dev` serves `index.html`, the chat alone.

The developer guide, [Developing Smarter Chat](https://docs.smarter.sh/smarter-framework/smarter-chat/development.html)
(`../smarter/docs/source/smarter-framework/smarter-chat/development.rst`),
explains the architecture in depth: read it before a non-trivial change.

## Non-negotiable rules

1. **Never run git write commands, or `npm publish` / `make release`.** "Write
   a git commit" means print the command. See `smarter-git-commits`. Releases
   are CI's (`doc/adr/013-ci-cd.md`).
2. **Run the tests yourself** after any change: `make test`, and `make lint`.
   After a change to `src/embed/`, `vite.config.ts` or a dependency, also
   `make build && npm run check:dist`. Never ask the user to re-run them, and
   report failures honestly. See `smarter-chat-testing`.
3. **Never edit `contract/` or `src/contract.gen.ts` by hand.** The platform
   owns the contract (`doc/adr/004-api-contract.md`).
4. **Every html string that reaches a chatscope `Message` comes from
   `messageFactory()`** in `src/lib/messages.ts`, and passes through DOMPurify.
   Validate every value from a page or a platform (`doc/adr/008-security.md`).
5. **No test or story calls a real Smarter platform or LLM.** MSW answers
   every request.
6. **The public api is broader than `src/index.ts`**: props, embed options,
   cookie names, class names and css properties are all public
   (`doc/adr/014-versioning.md`). Don't rename them in a `feat` or `fix`.
7. **Coverage:** at least 90%, 95% where it takes moderate effort.
8. **This repository is public.** No api keys, tokens, account numbers,
   private hostnames or customer data. Example urls use `example.com` and the
   fake account number `3141-5926-5359`.

## Two clones

There may be two working trees of this repository on the machine
(`doc/adr/003-repository.md`):

- `../smarter-chat` (this one), a plain clone, and
- `../smarter/smarter/react/packages/smarter-chat`, which the platform's
  `make react-install` clones into its npm workspace.

They are separate git repositories. A change in one is not in the other until
it is pushed and pulled. Make the change in the clone the user is working in,
and say which one you changed. Inside the workspace, `make init` installs the
whole workspace and `make build` writes the app into Django's static files.
Never commit this package from the platform's repository.

## Source map

| Path                                                             | Responsibility                                                                  |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `src/index.ts`                                                   | The library's public api                                                        |
| `src/main.tsx`                                                   | The dev server's page (`npm run dev`): props from the root element's attributes |
| `src/types.ts`                                                   | Props, and aliases of the generated contract types                              |
| `src/components/SmarterChat/`                                    | The chat: all of its state (`useState`, no store), the api calls' orchestration |
| `src/components/DocsDialog/`                                     | Sandbox mode's Docs dialog of technical references                              |
| `src/lib/api.ts`                                                 | Every request to the platform; the only module that calls `fetch`               |
| `src/lib/messages.ts`                                            | The thread, markdown to sanitized html                                          |
| `src/lib/styles.ts`                                              | The LLMClient's styles as `--smarter-chat-*` css properties, validated          |
| `src/lib/code.ts`, `math.ts`, `mermaid.ts`                       | highlight.js, KaTeX, Mermaid (lazy)                                             |
| `src/lib/cookie.ts`                                              | Session and debug cookies                                                       |
| `src/lib/i18n.tsx`, `locale/`, `src/catalogs.gen.ts`             | Translations: `gettext()`, the `.po` catalogs, the compiled catalogs            |
| `src/embed/`                                                     | The embed script. See `smarter-chat-embed`                                      |
| `src/mocks/`                                                     | Fixtures (copied from real responses), MSW handlers, fakes                      |
| `contract/`, `src/contract.gen.ts`, `scripts/contract-types.mjs` | The generated api contract                                                      |
| `scripts/check-dist.mjs`                                         | Checks the built package, and runs the embed script in jsdom                    |
| `vite.config.ts`                                                 | The two builds, the dev server, and the plugins each needs                      |

Components import from `@/` (`src/`); tests also from `@test/` (`test/`).

## Changes that cross into ../smarter

| Change                           | In ../smarter                                                                                                                                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A new field of the configuration | The model in `smarter/apps/prompt/contract/models.py` first (and `PUBLIC_LLMCLIENT_FIELDS` if public), then `make chat-contract` there, which copies the schema here and runs `npm run contract:types` |
| A new request header             | `CORS_ALLOW_HEADERS` in `smarter/settings/base.py`, or pages on other domains break                                                                                                                    |
| A prop that the workbench sets   | The workbench's `App.tsx` (`smarter/react/packages/smarter-workbench`), once a release with the prop is in the workspace's clone                                                                       |
| A new style setting              | The styles model of the LLMClient manifest, the contract, then the css variable in `src/lib/styles.ts` and `styles.css`                                                                                |
| Anything user-facing             | `docs/source/smarter-framework/smarter-chat*.rst` (evergreen prose; load the platform's `smarter-sphinx-docs` skill)                                                                                   |

`make chat-contract` runs in the platform's `smarter-app` container and copies
into the workspace clone (`SMARTER_CHAT_DIR`), not into `../smarter-chat`. If
you work here, copy `contract/chat-contract.schema.json` over and run
`npm run contract:types`. Each repository gets its own commit.

## Common changes

- **A prop:** `SmarterChatProps` in `src/types.ts` (optional, doc comment), a
  default in `SmarterChat`'s parameter list that suits the npm package's
  users, the README's props table and `embedding.rst`, a test, and a story if
  it changes what the chat looks like. If the embed script should pass it, see
  `smarter-chat-embed`.
- **A configuration field:** see the table above. Add it to `makeConfig()` in
  `src/mocks/fixtures.ts`, and read it with a fallback for platforms that
  don't send it, and for version 1 (`normalizeConfig()`).
- **A progress event type:** nothing is required (any `message` is shown). To
  treat one specially, switch on `event.type` in `onProgress`, and add an
  example to `progressEvents`.
- **A Console tab:** the Console is the platform's workbench's, not this
  package's: see the platform's `smarter/react/packages/smarter-workbench`.
- **Markdown:** a `marked` extension or renderer in `messages.ts`, following
  `math.ts`. Allow in `sanitize()` exactly the tags and attributes it emits.
- **A dependency:** check its license (`doc/adr/016-licensing.md`) and its
  effect on `embed.js`'s 400 kB gzip budget (`doc/adr/010-bundle-size.md`).
  If it's large and rarely needed, load it lazily, as Mermaid is.
- **Text that the chat displays:** wrap it in `gettext()` (or `ngettext`,
  `pgettext`) from `@/lib/i18n`, at render time, never in a module-level
  constant. The message is a string literal, a whole sentence, with named
  `%(name)s` placeholders filled by `interpolate()`; a count uses `ngettext`.
  Then `npm run i18n`, translate the new `msgstr`s in
  `locale/es/LC_MESSAGES/smarter-chat.po` and `locale/fr/...` (the console's
  terms: tú, "Modo de pruebas"; vous, "bac à sable"), check them with
  `msgfmt --check -o /dev/null <file>.po`, and run `npm run i18n` again.
  `src/catalogs.test.ts` fails on an out-of-date or untranslated catalog.
  Don't translate the LLMClient's text, the platform's messages, logs, or
  developer errors. See `doc/adr/018-translations.md`.
- **A language:** add it to `LANGUAGES` in `scripts/i18n.mjs` (the platform's
  `LANGUAGES` too, so the two match), `npm run i18n`, and translate its new
  `.po` file. Its test in `src/catalogs.test.ts` lists the languages.
- **A css file:** prefix classes `smarter-chat-`. In the embed script, it is

  shadow-root css automatically; `@font-face` rules are hoisted to the page.

## Related skills

| Skill                  | Use it when                                                      |
| ---------------------- | ---------------------------------------------------------------- |
| `smarter-chat-testing` | Writing or running tests and stories, coverage, `check:dist`     |
| `smarter-chat-embed`   | Changing `src/embed/`, an embed option, or the embed build       |
| `smarter-code-quality` | Before finishing: Prettier, ESLint, tsc and the pre-commit hooks |
| `smarter-git-commits`  | Asked to write a commit message                                  |
| `monthly-maintenance`  | Updating dependencies, re-syncing the contract                   |

In `../smarter`: `smarter-react-testing` (the workspace's shared test setup),
`smarter-django-react` (how Django hosts console apps), `smarter-sphinx-docs`.
