# ADR-003: Its Own Repository, Inside the Platform's Workspace

## Status

Accepted

## Context

Smarter Chat is one of the web console's React apps, which live in the platform's npm workspace, `smarter/react/packages/`. It is also a public npm package, with its own version, changelog and release cadence, which other repositories (the platform integrations) depend on.

## Decision

Smarter Chat has its own repository, `smarter-sh/smarter-chat`, where it is versioned, tested and released. The platform's `make react-install` clones it into `smarter/react/packages/smarter-chat` (`SMARTER_CHAT_BRANCH`, `main` by default), which the platform's `.gitignore` excludes, and the platform's CI clones it the same way before its React build.

The repository is **self-contained**: its TypeScript, Vite, Vitest, Storybook, ESLint and Prettier configuration are its own copies of the workspace's shared configuration, with the same behavior. So `make init`, `make test` and `make lint` work in a plain clone and inside the workspace, where `make init` installs the whole workspace, `make build` builds the app into Django's static files, and the workspace's Vitest runs this package's `vitest.config.ts` as one of its projects. `package-lock.json` is not committed: inside the workspace it is the workspace's.

## Alternatives Considered

- **A package of the platform's repository only.** The npm package's history and releases would be mixed with the platform's, and the integrations would depend on the platform's release cadence.
- **A git submodule.** Submodules are pinned to a commit, and easy to commit by accident from the parent; a clone that the parent ignores is simpler.
- **Thin per-package configuration that re-exports the workspace's**, as the other console apps have. It wouldn't work in a plain clone, or in this repository's CI.

## Consequences

- **Positive:**
  - The package can be developed, tested and released without the platform.
  - Inside the workspace, it is tested and linted with the other apps by the platform's `make react-test` and `make react-lint`.
- **Negative:**
  - A developer may have two clones: `smarter-chat/` and `smarter/smarter/react/packages/smarter-chat/`. They are separate working trees, and a change in one is not in the other until it is pushed and pulled. Commit from the clone you changed, never from the platform's repository.
  - The copied configuration must be kept in step with the workspace's by hand.
  - A cross-repository change, e.g. to the contract (ADR-004), takes one commit in each repository.

## Related ADRs

- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-004: The Api Contract Is Generated from the Platform](004-api-contract.md)
- [ADR-015: Code Quality](015-code-quality.md)
