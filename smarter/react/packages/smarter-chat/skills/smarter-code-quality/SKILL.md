---
name: smarter-code-quality
description: Use before finishing any change to smarter-chat, to format, lint and type-check it - Prettier, ESLint (typescript-eslint, React hooks, jsx-a11y, Storybook, Testing Library, Vitest), tsc, codespell, the generic pre-commit hooks and commitlint. Explains which tools are authoritative, how to run them on changed files under zsh, and the traps (generated contract types, NODE_ENV, running inside the platform's workspace).
---

# Smarter Chat: Code Quality

`.pre-commit-config.yaml`, `eslint.config.js`, `.prettierrc.json` and the
`tsconfig*.json` files are the standard, and match the platform's React
workspace (`doc/adr/015-code-quality.md`). If a hook passes, the code meets it;
if it fails, fix the code. Never bypass a hook (`--no-verify`, `SKIP=`), and
never add an `eslint-disable` without a comment that says why.

| Tool       | Configuration                             | Notes                                                                    |
| ---------- | ----------------------------------------- | ------------------------------------------------------------------------ |
| Prettier   | `.prettierrc.json`, `.prettierignore`     | 120 columns. Formats ts, tsx, css, md, yaml, json                        |
| ESLint     | `eslint.config.js`                        | `--max-warnings=0`. Tests get Testing Library, jest-dom and Vitest rules |
| TypeScript | `tsconfig.app.json`, `tsconfig.node.json` | `npm run typecheck` (`tsc -b`). Unused locals and parameters are errors  |
| codespell  | `codespell.txt`                           | Real project words go in `codespell.txt`                                 |
| commitlint | `commitlint.config.cjs`                   | Commit-msg hook. Header 72 characters at most                            |

## How to run

```console
make lint                                                    # eslint, tsc, prettier --check: what CI runs
make format                                                  # prettier --write .
git diff --name-only | xargs pre-commit run --files
git ls-files --others --exclude-standard | xargs pre-commit run --files   # new files
```

Use `xargs`: under zsh, `--files $FILES` is one argument. pre-commit is in
`venv/` after `make python-init`, or in `../smarter/venv`.

## Traps

- `src/contract.gen.ts` is generated: if a hook or tsc complains about it,
  regenerate it (`npm run contract:types`), never edit it.
- Unused variables are errors except those named `_` or `_x` (the ignored half
  of a pair).
- `react-refresh/only-export-components` is off only for stories, tests and
  mocks. A component module that also exports a helper fails; move the helper
  to `src/lib/`.
- If `npx eslint` is missing, `NODE_ENV=production` made npm skip
  devDependencies: `npm install --include=dev`.
- Inside the platform's workspace, the hooks find Prettier and ESLint in
  `../../node_modules/.bin`; the platform's `make react-lint` lints this package
  with the others.

## Principles

- Match the surrounding code: module comments that say what a module is for
  and where it fits, doc comments on exports, comments that say why.
- Name things for the reader: `smarter-chat-` css classes, `--smarter-chat-*`
  properties, `loggerPrefix` in console messages.
- `console.debug` is stripped from production builds; `console.error` isn't,
  and is for the page's developer (a bad option, a missing target).
