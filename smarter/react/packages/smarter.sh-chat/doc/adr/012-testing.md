# ADR-012: Testing

## Status

Accepted

Follows the platform's [ADR-013: Testing](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/013-testing.rst), and its React workspace's conventions (the platform's `smarter-react-testing` skill).

## Context

The chat depends on a Smarter platform, an LLM and the browser. Tests that needed a running platform couldn't run in this repository's CI, and would be slow, billable and flaky. Tests against hand-written responses can pass against responses the platform never sends.

## Decision

- **Vitest with React Testing Library and `user-event`, in jsdom.** One test module per source module, beside it. Tests query by role and label, and assert what a user sees.
- **The api is mocked with MSW**, in tests and Storybook alike, from one set of fixtures (`src/mocks/fixtures.ts`, copied from real responses) and handlers grouped by scenario (`src/mocks/handlers.ts`). An unhandled request fails the test (`onUnhandledRequest: "error"`).
- **The fixtures match the contract**: `src/contract.test.ts` validates them against the platform's JSON Schema, in both versions (ADR-004).
- **Every story is a test**: `src/stories.test.tsx` renders each story in `*.stories.tsx`, with its handlers, and runs its `play` function. A new visual state gets a story.
- **jsdom's gaps get named doubles**, not ad hoc mocks: `FakeEventSource` (`src/mocks/fakes.ts`) for the log stream, and a fake Mermaid (`src/mocks/mermaid.ts`), because jsdom can't lay out svg.
- **The built package is tested too**: `scripts/check-dist.mjs` loads `dist/embed.js` into a jsdom page and checks the launcher, its shadow root and css, `window.SmarterChat.version`, the production build and the size budget (ADR-010). It never opens the launcher, so it makes no request.
- `vitest.config.ts` forces `NODE_ENV=test`, `TZ=UTC` and `LANG=en_US.UTF-8`, so results don't depend on the machine.
- **Coverage**: at least 90%, 95% where it takes moderate effort; Codecov requires 90% of a pull request's changed lines, and fails a commit that lowers the total by more than 1%.

No test calls a real Smarter platform or an LLM.

## Alternatives Considered

- **End-to-end tests against a platform**, e.g. Playwright. They belong to the platform, which can run one; here they would need credentials and a deployed LLMClient in CI.
- **Mocking `fetch` or `api.ts` per test.** MSW tests the real request code, and the same handlers serve Storybook.
- **Snapshot tests.** They assert markup, not behavior, and are approved without being read.

## Consequences

- **Positive:**
  - The tests run in seconds, anywhere, without secrets.
  - Stories can't rot, and fixtures can't drift from the platform.
- **Negative:**
  - Real rendering of Mermaid, layout and the shadow root in a browser are checked only in Storybook, and by `check:dist` in jsdom.

## Related ADRs

- [ADR-004: The Api Contract Is Generated from the Platform](004-api-contract.md)
- [ADR-011: Accessibility](011-accessibility.md)
- [ADR-013: CI/CD and Releases](013-ci-cd.md)
