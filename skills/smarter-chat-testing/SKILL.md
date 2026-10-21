---
name: smarter-chat-testing
description: Use when writing, fixing or running Smarter Chat's tests or Storybook stories (smarter/react/packages/smarter.sh-chat, the @smarter.sh/ui-chat npm package), or raising its coverage. Covers Vitest with React Testing Library in jsdom, MSW fixtures and handlers shared with Storybook, every story rendered as a test, the contract test that validates fixtures against the platform's JSON Schema, FakeEventSource and the fake Mermaid, testing the embed script and its shadow root, scripts/check-dist.mjs, coverage, and the pitfalls.
---

# Smarter Chat: Testing

The decisions are in `doc/adr/012-testing.md`. Paths are relative to
`smarter/react/packages/smarter.sh-chat`. The package follows the same
conventions as the rest of the workspace (`smarter-react-testing`), but keeps
its own copies of the configuration: `vitest.config.ts`, `test/` and
`.storybook/`, because it is also built and published on its own.

## Commands

```console
cd smarter/react
npx vitest run --project smarter.sh-chat                  # the package's tests
npx vitest run --project smarter.sh-chat -t "restores the thread"   # one test by name
npm run lint -w @smarter.sh/ui-chat                       # eslint
npm run typecheck -w @smarter.sh/ui-chat                  # tsc
npm run build -w @smarter.sh/ui-chat && npm run check:dist -w @smarter.sh/ui-chat   # the built package, and the embed script in a page

cd smarter/react/packages/smarter.sh-chat
npm run coverage                                          # text summary, and coverage/index.html
npx vitest run src/lib/api.test.ts                        # one file

make react-storybook APP=smarter.sh-chat                  # Storybook at http://localhost:6006, from the repository's root
make react-test                                           # every package, with the workspace's coverage report
make react-lint                                           # formatting, lint and types of every package, as CI does
```

Save the full output to a file in your scratchpad and read its summary:
**check the "Test Files" line**, not just "Tests". A file that fails to load
(an import or `vi.mock` error) still lets its siblings report "passed". Use
`NO_COLOR=1`, or `grep -a`, because colored output looks binary to `grep`.

## Conventions

- **One test module per source module**, beside it: `api.test.ts`,
  `Component.test.tsx`. `describe`/`it`/`expect` are imported from `vitest`
  (globals are off).
- **Query as a user does**: `getByRole`, `findByRole`, `getByLabelText`,
  `getByText`. No test ids or class selectors, except for markup that chatscope
  renders as html strings. Interact with `userEvent.setup()`.
- **The api is MSW.** `test/setup.ts` starts the server with
  `onUnhandledRequest: "error"`, and resets handlers, storage and cookies after
  each test. Add a test's responses with `server.use(...)`, from the scenario
  groups in `src/mocks/handlers.ts` (`chatHandlers`, `historyHandlers`,
  `promptErrorHandlers`, `loadingHandlers`, streaming handlers, ...). Within one
  `server.use(a, b)`, the first matching handler wins; a later `server.use`
  call wins over an earlier one.
- **Fixtures are real.** `src/mocks/fixtures.ts` is trimmed from real
  responses, built with `makeConfig()`. `src/contract.test.ts` validates every
  exported fixture against `contract/chat-contract.schema.json`; a new fixture
  goes into that test's list too. If a fixture fails the schema, the fixture is
  wrong, or the platform's contract changed: regenerate it with
  `make chat-contract` (`smarter-chat-development`), don't loosen the test.
- **Every story is a test** (`src/stories.test.tsx`). A new visual state gets
  a story (CSF3, `parameters: { msw: { handlers } }`, a `play` function for
  interactions); a story that stops rendering fails the tests.
- **jsdom's gaps:** Mermaid is mocked with `src/mocks/mermaid.ts` via an async
  `vi.mock` factory (factories are hoisted above imports).
- **Hostile input:** tests of `messages.ts`, `styles.ts` and `embed/options.ts`
  include `<script>`, `javascript:` and svg `data:` urls, and css injection
  (`red; background:url(...)`). Add such a case for any new rendered value.

## Testing the embed script

- `src/embed/*.test.ts` test each module directly: `parseOptions()` with a
  `get` function, `mountChat()` and `autoMount()` with a document, the element
  after `defineElement()`. Query inside `element.shadowRoot`.
- `src/embed/index.ts` has side effects when imported (it defines the element
  and reads `window.SmarterChatConfig`); `index.test.ts` resets modules and
  globals around each import. Follow it.
- `scripts/check-dist.mjs` runs the **built** `dist/embed.js` in jsdom: the
  files, the 400 kB gzip budget, the production build, the launcher in its
  shadow root, no css leaking into the page's head, and the version. Run it
  after any change to `src/embed/`, `vite.config.ts` or a dependency. It never
  opens the launcher, so it makes no request. `uiChatRelease.yml` runs it
  before every publish.

## Pitfalls

- **`NODE_ENV=production` in your shell** makes React load its production
  build (`React.act is not a function`), and npm skip devDependencies.
  `vitest.config.ts` forces `NODE_ENV=test`; if `npx vitest` is missing, run
  `make react-install`.
- Dates and locales are pinned (`TZ=UTC`, `en_US.UTF-8`) in `vitest.config.ts`.
- Coverage is configured in `vitest.coverage.config.ts`, not
  `vitest.config.ts`: the workspace runs the latter as a project, and a project
  can't configure coverage. Stories, tests, mocks and `main.tsx` are excluded.
  The workspace's own coverage report (`make react-test`) includes the package
  too.
- `.storybook/` is not only Storybook's: `test/setup.ts` imports
  `.storybook/parameters`, and the tsconfigs include its files. Don't ignore
  or move it.

## Never

- Never point a test, a story or `check:dist` at a real Smarter platform, or
  use a real api key.
- Never mock `fetch` or `src/lib/api.ts` to avoid writing a handler.
- Never weaken `contract.test.ts` to make a fixture pass.
