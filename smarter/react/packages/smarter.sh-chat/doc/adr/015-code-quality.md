# ADR-015: Code Quality

## Status

Accepted

Follows the platform's [ADR-028: Code Quality](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/028-code-quality.rst), and its React workspace's configuration.

## Context

The package is developed in a plain clone and inside the platform's workspace (ADR-003), by people and coding agents. Formatting and lint must be the same in both, and checked before a commit, not discovered in CI.

## Decision

- **Prettier** formats TypeScript, css, Markdown, YAML and JSON (`.prettierrc.json`: 120 columns, double quotes, trailing commas).
- **ESLint** (flat config, `eslint.config.js`, `--max-warnings=0`): TypeScript, React hooks, React Refresh, `jsx-a11y`, Storybook, and Testing Library, jest-dom and Vitest rules for tests, then `eslint-config-prettier`.
- **TypeScript** type-checks the whole repository (`npm run typecheck`, `tsc -b`), with unused locals and parameters as errors.
- **pre-commit** (`.pre-commit-config.yaml`) runs codespell, Prettier, ESLint and the standard checks on each commit, and **commitlint** (conventional and angular rules, a 72-character header) on each commit message. Prettier and ESLint run from this repository's `node_modules`, or the workspace's.
- `make lint` is what CI runs: ESLint, TypeScript and `prettier --check`.
- Generated files (`src/contract.gen.ts`) are never edited by hand, and the MSW worker in `.storybook/public/` is ignored.
- Comments explain why, in plain sentences; module comments say what a module is for and where it fits.

## Alternatives Considered

- **Biome, or Ruff-style all-in-one tools.** They would diverge from the platform's workspace, which uses Prettier and ESLint.

## Consequences

- **Positive:**
  - A commit that passes its hooks passes CI's lint.
- **Negative:**
  - The hooks need `make init` (for `node_modules`) and `make python-init` or a global pre-commit.

## Related ADRs

- [ADR-003: Its Own Repository, Inside the Platform's Workspace](003-repository.md)
- [ADR-013: CI/CD and Releases](013-ci-cd.md)
