# CLAUDE.md

Guidance for Claude Code (and other coding agents) working in this repository.

smarter-chat is **Smarter Chat**, the npm package `@smarter.sh/ui-chat`: the
React chat UI of Smarter LLMClients. One source builds two things: a React
library, which the Smarter web console's Prompt Engineer's Workbench (the
platform's `@smarter/workbench` app) imports too, and `dist/embed.js`, a
self-contained script that adds the chat to any web page
and that the platform integrations (`../smarter-wordpress`,
`../smarter-drupal`, `../smarter-shopify`, `../smarter-gtm-template`,
`../smarter-docs-site-generators`) load from jsDelivr. The chatbot itself is
an LLMClient on a Smarter platform
([smarter-sh/smarter](https://github.com/smarter-sh/smarter), `../smarter`).

Detailed know-how lives in the Agent Skills under `skills/` (symlinked to
`.claude/skills`). **Load `smarter-chat-development` first for any change.**
The decisions behind the code are in `doc/adr/`. This file holds only what
applies to nearly every task.

## Hard rules

1. **Never run git write commands**, here, in `../smarter` or in any other
   repository. "Write a git commit" means print the command as text. See
   `smarter-git-commits`.
2. **Never publish.** No `npm publish`, `make release`, or `npm login`.
   Releases are built and published by CI (`doc/adr/013-ci-cd.md`).
3. **Run the tests yourself** after any change (`make test`, `make lint`),
   and `make build && npm run check:dist` after changing `src/embed/`,
   `vite.config.ts` or a dependency. Never ask the user to re-run them.
   Report failures honestly.
4. **Never edit `contract/` or `src/contract.gen.ts` by hand.** The platform
   generates the contract.
5. **No test, story or script calls a real Smarter platform or LLM.** MSW
   answers every request.
6. **Sanitize and validate.** Html reaches the chat only through
   `src/lib/messages.ts`; every value from a page or a platform is validated
   (`doc/adr/008-security.md`).
7. **The pre-commit hooks, ESLint, tsc and Prettier are the lint standard.**
   See `smarter-code-quality`.
8. **Coverage:** at least 90%, 95% where it takes moderate effort.
9. **This repository is public.** No api keys, tokens, account numbers,
   private hostnames, names or customer data in code, tests, docs or skills.

## Repository map

| Path                 | Contents                                                                        |
| -------------------- | ------------------------------------------------------------------------------- |
| `src/index.ts`       | The library's public api                                                        |
| `src/main.tsx`       | The dev server's page (`npm run dev`)                                           |
| `src/components/`    | `SmarterChat` (and its `HeaderButton`), `AppTitle`, `ErrorBoundary`             |
| `src/lib/`           | Api calls, messages and markdown, styles, cookies, math, diagrams               |
| `src/embed/`         | The embed script and the `<smarter-chat>` element                               |
| `src/mocks/`         | Fixtures, MSW handlers and fakes for tests and stories                          |
| `contract/`          | The api contract's JSON Schema, copied from the platform                        |
| `scripts/`           | Contract type generation, and the built package's check                         |
| `test/`              | Vitest setup, the MSW server, stories-as-tests                                  |
| `.github/workflows/` | `test.yml`, `build.yml`, `pushMain.yml` (semantic-release), `release.yml` (npm) |
| `doc/adr/`           | Architecture decision records                                                   |
| `skills/`            | Agent Skills                                                                    |

The user documentation on docs.smarter.sh lives in the platform's repository:
`../smarter/docs/source/smarter-framework/smarter-chat.rst` and
`smarter-chat/*.rst`. The platform's `make react-install` also clones this
repository into `../smarter/smarter/react/packages/smarter-chat`, a separate
working tree.

## Common commands

```bash
make init                 # npm install
make serve                # Storybook at http://localhost:6006, api mocked
make test                 # Vitest
make coverage             # with coverage in coverage/
make lint                 # ESLint, tsc, prettier --check
make build                # the app, the library and the embed script
npm run check:dist        # check dist/, and run embed.js in jsdom
npm run contract:types    # regenerate src/contract.gen.ts from contract/
git diff --name-only | xargs pre-commit run --files
```

## Definition of done

- The change follows an existing pattern and the ADRs in `doc/adr/`.
- Tests cover it, and you ran them; `check:dist` passes when the build changed.
- ESLint, tsc, Prettier and the pre-commit hooks pass on the changed files.
- The README and docs.smarter.sh describe user-facing changes.
- Your summary says what changed, what you verified, and what you skipped.
