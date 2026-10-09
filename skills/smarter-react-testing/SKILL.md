---
name: smarter-react-testing
description: Use when writing or fixing Storybook stories, Vitest tests, MSW mocks, ESLint or Prettier issues in the Smarter React workspace (smarter/react). Covers the shared configuration, the per-package wiring, story and test conventions, the make targets and CI job, and the known pitfalls (silent file-load failures, NODE_ENV=production, locale, EventSource, vi.mock factories).
---

# Smarter React Testing and Code Quality

The workspace follows the React community's standard stack:

- **Storybook 10** (CSF3 stories, `@storybook/react-vite`, addon-docs, addon-a11y)
- **Vitest** with **React Testing Library**, `user-event` and jest-dom, in jsdom
- **MSW 2** (Mock Service Worker) for the Django API, shared by stories and tests
- **Prettier** for formatting, and **ESLint** (flat config) for lint
- Prettier and ESLint also run as **pre-commit** hooks, and in CI

## Commands

```console
make react-install                               # npm install, needed by the pre-commit hooks too
make react-test                                  # every package's tests, with coverage (smarter/react/coverage/)
make react-lint                                  # prettier --check, eslint, tsc: what CI runs
make react-storybook APP=smarter-secret-list     # one package's Storybook on http://localhost:6006

cd smarter/react
npx vitest run packages/smarter-secret-list      # one package
npx vitest run -t "lists your own"               # one test by name
npm run format && npm run lint:fix               # fix formatting and auto-fixable lint
```

CI: the `react` job in `.github/workflows/test.yml` runs `npm ci`,
`format:check`, `lint`, `typecheck`, and `coverage`.

## Shared configuration (in `smarter/react/`)

| File                                              | Purpose                                                                                                                                                                                                     |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vitest.shared.ts`                                | `smarterVitestProject(dir)`: jsdom at `http://localhost:9357/`, the setup file, `@smarter/common` → its source, `@/` → `src/`, `@test/` → `test/`. Forces `NODE_ENV=test`, `TZ=UTC`, and `LANG=en_US.UTF-8` |
| `vitest.config.ts`                                | Runs every package as one Vitest workspace, with coverage                                                                                                                                                   |
| `test/setup.ts`                                   | jest-dom matchers, the MSW server (`onUnhandledRequest: "error"`), relative `fetch()` URLs, and cleanup of the DOM, storage and cookies after each test                                                     |
| `test/server.ts`                                  | The MSW node server, which tests extend with `server.use(...)`                                                                                                                                              |
| `test/stories.ts`                                 | `testStories()`: renders every story, and runs its play function, as a test                                                                                                                                 |
| `storybook/main.ts`                               | `smarterStorybookConfig(dir)`: stories, addons, MSW worker, web console CSS, and Vite build-only plugins removed                                                                                            |
| `storybook/preview.ts`, `storybook/parameters.ts` | The MSW loader (`parameters.msw.handlers`) and shared parameters                                                                                                                                            |
| `eslint.config.js`                                | TypeScript, React hooks, React Refresh, jsx-a11y, Storybook, Testing Library, jest-dom, and Vitest rules, then eslint-config-prettier                                                                       |
| `.prettierignore`                                 | Build output, coverage, the generated MSW worker, and CHANGELOGs                                                                                                                                            |

## Per-package wiring

Each package has thin files that re-export the shared configuration. Copy them
from any package, for example `packages/smarter-guardrail-list/`:

- `.storybook/main.ts` → `smarterStorybookConfig(import.meta.dirname)`
- `.storybook/preview.ts` → `export { default } from "../../../storybook/preview"`
- `vitest.config.ts` → `smarterVitestProject(import.meta.dirname)`
- `eslint.config.js` → `export { default } from "../../eslint.config.js"`
- `tsconfig.app.json` → includes `../../test` and `../../storybook`, with the
  path `"@test/*": ["../../test/*"]`
- `package.json` scripts: `storybook`, `build-storybook`, `test`, `test:watch`,
  and `typecheck`
- `src/stories.test.tsx` →
  `testStories(import.meta.glob("./**/*.stories.tsx", { eager: true }))`
- `src/mocks/fixtures.ts` (a `sessionContext`, `makeObject()`, and owned and
  shared objects) and `src/mocks/handlers.ts` (`listHandlers()`,
  `actionHandlers`, and error handlers)

## Writing stories

- One `Component.stories.tsx` next to each component, plus `App.stories.tsx`.
- CSF3: `const meta = { title: "<App Name>/<Component>", component, args, parameters } satisfies Meta<typeof C>`,
  then `export const Default: Story = {}` and named variants (`Loading`,
  `Empty`, `Error`, ...).
- API calls are answered by `parameters: { msw: { handlers: [...] } }`, using the
  package's `src/mocks/handlers.ts`. Never call a real server.
- Use `play` functions for interactions. They run in Storybook and as tests.
- Every story is a test, so a story that stops rendering fails `make react-test`.

## Writing tests

- `Component.test.tsx` next to the component. Use `describe`, `it`, and `expect`
  imported from `vitest` (globals are off).
- Query the way a user perceives the page: `getByRole`, `findByRole`,
  `getByLabelText`, `getByText`. Avoid test ids and class selectors.
- Interact with `userEvent.setup()`, not `fireEvent`.
- Mock the network with `server.use(...handlers)`, not by mocking `fetch` or
  modules. Unhandled requests fail the test.
- Within one `server.use(a, b)` call, the **first** matching handler wins. A later
  `server.use(...)` call takes precedence over an earlier one.
- Assert on outcomes the user sees (rows, messages, error text), not on internal
  state.

## Pitfalls (each one cost real time)

- **"Tests N passed" can hide a failing file.** When a test file fails to load
  (an import or `vi.mock` error), Vitest still reports its other tests as passed.
  Always check the **"Test Files"** line for failures.
- **Don't pipe test output straight into `grep`.** Vitest's and npm's output
  contains ANSI color codes, so `grep` can treat it as binary and silently drop
  the summary lines ("Test Files", "Tests", "FAIL"). Save the complete output to
  a file, and search it with `grep -a`, or turn the colors off with
  `NO_COLOR=1 npm run test -w <package>`. Confirm the pass and fail counts
  before reporting a result.
- **`NODE_ENV=production` in your shell** makes React load its production build,
  and tests fail with "React.act is not a function". `vitest.shared.ts` forces
  `NODE_ENV=test`. Keep it that way.
- **Locale and time zone**: amounts rendered as "US$" and shifted dates come
  from the machine's locale. They're pinned in `vitest.shared.ts`.
- **MSW's `sse()` needs a global `EventSource` when the handler is created**,
  which jsdom lacks. Define a stub in `vi.hoisted(...)` before importing the
  handlers.
- **`vi.mock` factories are hoisted** above imports, so a factory that references
  an imported binding fails, especially with eager `import.meta.glob`. Use an
  async factory with `await import(...)`.
- **ESLint's flat config resolves file globs from the config file's own
  directory.** An override in the workspace config for
  `packages/smarter-common/...` doesn't apply when ESLint runs inside that
  package. Repeat it in the package's own `eslint.config.js` (as
  `smarter-common` does).
- **The pre-commit hooks use `npx --no-install`.** Without `make react-install`,
  they fail instead of downloading tools.

## Coverage

`make react-test` and CI run `npm run coverage` (`vitest run --coverage`).
Plain `npm test` doesn't collect coverage. A text summary prints to the
terminal, and the full report is written to `smarter/react/coverage/`. Open
`index.html` there for overall and per-file coverage. CI uploads `lcov.info` to
Codecov under the `react` flag. `lcov-report/` is just a duplicate of the HTML
report. No coverage thresholds are enforced, so a drop in coverage won't fail
the run.

**Target:** at least 95% for each react app, but higher is better. Use judgment
about when enough is enough. Large blocks of coverage misses in a module are
frowned upon. Individual tsx files with coverage ratios far below the 95% target
are also frowned upon. (see `smarter-development`).
