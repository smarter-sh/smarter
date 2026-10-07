# React Apps for the Smarter Web Console

This directory contains the React app npm workspace for the Smarter web console.

## Overview

The React frontend is organized as an npm workspace with standardized packages
under `packages/*`.

Key points:

- All package names are namespaced under `@smarter`.
- `@smarter/common` is the shared dependency package and must be built first.
- React app builds are managed with [Vite.js](https://vite.dev/).
- App structure, build behavior, and dependency patterns are
  standardized across packages.
- Build artifacts are written into Django static paths and then collected by Django.

## Build For Production

Use the convenvience commands in Makefile to build all packages and integrate
to Django.

```console
make react-install
make react-build
make collectstatic
make build
make run
```

## Workspace Layout

- Root workspace manifest: `smarter/react/package.json`
- Packages directory: `smarter/react/packages`
- Shared package: `smarter/react/packages/smarter-common`

Current app packages include:

- `smarter-authtoken-list`
- `smarter-budget-list`
- `smarter-common`
- `smarter-connection-list`
- `smarter-custom-domain-list`
- `smarter-dashboard`
- `smarter-guardrail-list`
- `smarter-llmhost-compute-list`
- `smarter-llmhost-list`
- `smarter-manifest-dropzone`
- `smarter-manifest-editor`
- `smarter-mcpclient-list`
- `smarter-orchestrator-list`
- `smarter-plugin-list`
- `smarter-prompt-list`
- `smarter-prompt-passthrough`
- `smarter-provider-list`
- `smarter-proxy-list`
- `smarter-secret-list`
- `smarter-terminal-emulator`
- `smarter-vectorsearch-list`
- `smarter-vectorstore-list`

## Workspace Build Orchestration

The workspace root uses npm workspaces and a build script that enforces build order:

```json
{
  "private": true,
  "workspaces": ["packages/*"],
  "scripts": {
    "build": "npm run build --workspace=@smarter/common && npm run build --workspaces --exclude=@smarter/common"
  }
}
```

Why this matters:

- `@smarter/common` is compiled first.
- All other packages that depend on `@smarter/common` build afterwards.
- This avoids dependency ordering issues and keeps builds deterministic.

## Standard Local Development Build Procedure

To build and run all React apps from the repository root,
run the following steps in order:

1. `make react-install`
   Creates shared `node_modules` for the React workspace.
2. `make react-build`
   Builds each React package and writes output into Django static path under `smarter/static/react`.
3. `make collectstatic`
   Consolidates static assets into Django `staticfiles`.
4. `make build`
   Builds the Docker container.
5. `make run`
   Starts the web console, typically served on localhost.

## Typical Package Pattern

A typical app package:

- Name format: `@smarter/<app-name>`
- Build stack: TypeScript + Vite
- Common dependency: `@smarter/common`
- Local commands usually include:
  - `dev`
  - `build`
  - `lint`
  - `preview`
  - `typecheck`
  - `test` and `test:watch`
  - `storybook`
  - `build-storybook`

Example package manifest reference: [packages/smarter-authtoken-list/package.json](./packages/smarter-authtoken-list/package.json)

## Stories (Storybook)

Every app documents its components as [Storybook](https://storybook.js.org/) stories, in
[Component Story Format 3](https://storybook.js.org/docs/api/csf): a `Component.stories.tsx` next to each
component, and an `App.stories.tsx` for the whole app. Each story renders one state of a component, from
the example data in the app's `src/mocks/`: e.g. a list that is loading, empty, or failed to load.

```console
make react-storybook APP=smarter-secret-list    # or: cd packages/smarter-secret-list && npm run storybook
```

- The Storybook configuration is shared: each package's `.storybook/main.ts` and `preview.ts` delegate to
  [storybook/main.ts](./storybook/main.ts) and [storybook/preview.ts](./storybook/preview.ts).
- Stories that call the Django api declare its responses as [MSW](https://mswjs.io/) request handlers, in
  `parameters.msw.handlers`. The app's `src/mocks/handlers.ts` holds them; `src/mocks/fixtures.ts` holds the
  example data. No Django server is needed, though its stylesheets are loaded from it, if it is running, so
  that components look as they do in the web console.
- A story's `play` function scripts a user interaction, e.g. the Toolbar's `Delete` story, which confirms a
  delete. It runs in Storybook, and in the tests.
- `@storybook/addon-docs` generates a docs page per component, and `@storybook/addon-a11y` reports each
  story's accessibility violations.

## Testing

The apps are tested with [Vitest](https://vitest.dev/) and
[React Testing Library](https://testing-library.com/docs/react-testing-library/intro/), in jsdom.

```console
make react-test                  # every app, with a coverage report in coverage/
npm test                         # every app, in smarter/react
npm run test:watch               # in a package: re-run its tests on each change
```

- Tests are `*.test.ts(x)` files next to the code that they test. Following Testing Library's guidance,
  they find elements as a user does, by role and accessible name, e.g.
  `screen.getByRole("button", { name: /^Delete:/ })`, and act as a user does, with `user-event`.
- Api requests are answered by MSW, with the same handlers as the stories. A request without a handler
  fails the test, so a test never reaches a real server.
- Every story is also a test: each package's `src/stories.test.tsx` renders all of its stories, and runs
  their `play` functions. A story that stops rendering, e.g. after a component's props change, fails.
- The shared setup is in [vitest.shared.ts](./vitest.shared.ts) and [test/](./test/). It pins `NODE_ENV`,
  the time zone and the locale, so that tests behave the same on every machine and in CI.
- What jsdom cannot run is replaced in tests: the Monaco editor by a textarea, and xterm.js and
  `EventSource` by fakes (see `src/mocks/` in those apps).

## Code Quality

The React counterparts of the repository's Python tooling:

| Python         | React                                                                                                                              | Command                                  |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| black          | [Prettier](https://prettier.io/)                                                                                                   | `npm run format`, `npm run format:check` |
| flake8, pylint | [ESLint](https://eslint.org/), with TypeScript, React hooks, accessibility (jsx-a11y), Storybook, Testing Library and Vitest rules | `npm run lint`                           |
| mypy           | TypeScript                                                                                                                         | `npm run typecheck`                      |
| pytest         | Vitest                                                                                                                             | `npm test`                               |

- pre-commit runs Prettier and ESLint on the React files of each commit, with the workspace's own
  versions and configuration ([eslint.config.js](./eslint.config.js), and the repository's
  `.prettierrc.json`). Install the workspace's dependencies first: `make react-install`.
- `make react-lint` checks formatting, lint and types, and CI's `react` job (`.github/workflows/test.yml`)
  runs all four.

## Adding an App

A new package gets the shared configuration by copying these files from an existing app, unchanged:
`.storybook/main.ts`, `.storybook/preview.ts`, `vitest.config.ts`, `eslint.config.js`, and the
`typecheck`, `test`, `test:watch`, `storybook` and `build-storybook` scripts of its `package.json`. Its
`tsconfig.app.json` includes `../../test` and `../../storybook`, and maps `@test/*` to `../../test/*`.
Then add `src/mocks/`, stories, tests, and a `src/stories.test.tsx`.

## Vite and Django Integration

Each app uses a standardized Vite configuration to support Django integration
and deployment workflows.

Example vite config: [packages/smarter-authtoken-list/vite.config.ts](./packages/smarter-authtoken-list/vite.config.ts)

Common behavior includes:

- Output directory points to Django static React folder: [smarter/smarter/static/react/@smarter](../smarter/static/react/@smarter/)
- Build manifest is generated and used by Django template tags for hashed asset
  resolution.
- Custom metadata is injected into `manifest.json` after build.
- Optional post-build CDN deploy can sync to S3 and invalidate CloudFront when
  enabled in package config.
- Vite dev server proxies API and static routes to Django so app behavior in
  development is close to runtime behavior.
- Production builds remove `console.debug` via the Oxc minifier's `manualPureFunctions` configuration.
- xterm-related dependencies may be chunked separately for better browser caching.

## Standardization Rules Across Apps

To keep all React apps consistent:

- Use `@smarter` namespace for package names.
- Depend on `@smarter/common` for shared functionality.
- Keep scripts and tooling aligned with the common pattern.
- Use Vite config conventions that target Django static integration.
- Preserve proxy behavior needed for local Django-backed development.
- Keep manifest behavior consistent so Django asset resolution remains reliable.

## Practical Notes

- If a package depends on `@smarter/common`, do not build it before common is built.
- If static assets appear stale in Django, re-run:
  1. `make react-build`
  2. `make collectstatic`
- For local feature work on a single package, use that package `dev` command, but
  follow the full build pipeline before integration testing through Django and Docker.
