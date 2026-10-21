---
name: monthly-maintenance
description: Use when asked to do smarter-chat's monthly maintenance, or part of it - update the npm dependencies (minor and major, React, Vite, Vitest, Storybook, ESLint, TypeScript, Mermaid, KaTeX), pre-commit's hooks and the GitHub Actions versions, re-sync the api contract with the platform, retest (lint, tests, coverage, the build and check:dist with the embed script's size budget), and write a "fix" or "chore" git commit.
---

# Monthly Maintenance

1. **Baseline.** On a clean tree, run `make lint`, `make coverage`, and
   `make build && npm run check:dist`, and note the results, the coverage and
   `embed.js`'s gzipped size, so that you can tell new failures from old ones.
2. **The contract.** Compare `contract/chat-contract.schema.json` with
   `../smarter/smarter/smarter/apps/prompt/contract/chat-contract.schema.json`.
   If they differ, copy the platform's, run `npm run contract:types`, and fix
   fixtures and code until `make test` passes (`smarter-chat-development`). Read
   the platform's commits to `smarter/apps/prompt/` since the last release for
   new fields, progress event types and headers worth using.
3. **npm dependencies.** `npx npm-check-updates` to list them, then
   `npm update` for minor versions, and majors one family at a time
   (Storybook's packages together; Vite with `@vitejs/plugin-react`; Vitest
   with `@vitest/coverage-v8` and `@vitest/eslint-plugin`; ESLint with its
   plugins). Read each major's migration notes. Keep `react`/`react-dom` and
   the `peerDependencies` range in step. `package-lock.json` isn't committed
   (`doc/adr/003-repository.md`); `package.json` is.
4. **Watch the embed script.** A new Mermaid, KaTeX, marked or chatscope can
   change rendering and size: check the `WithDiagram`, math and styles stories
   in Storybook (`make serve`), and the size that `check:dist` reports against
   the baseline.
5. **Hooks and workflows.** `pre-commit autoupdate` (CI also does it weekly),
   and the `uses:` versions in `.github/workflows/` and `.github/actions/`
   (Dependabot proposes them too).
6. **Test.** `make lint`, `make coverage`, `make build && npm run check:dist`.
   All must pass, with coverage no lower than the baseline, before a commit.
7. **Commit.** Load `smarter-git-commits`. A dependency update that users can
   notice (rendering, size, a security fix) is a `fix(deps)`, which releases
   it; tooling only (dev dependencies, hooks, CI) is `chore(deps)` or
   `ci`. List each major update, and the size before and after.

If a new release follows, the integrations pick it up in their own monthly
maintenance (`smarter-chat-embed`, "Carrying a release to the integrations").
