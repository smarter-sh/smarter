# ADR-020: Part of the Platform's Repository

## Status

Accepted

Supersedes [ADR-003](003-repository.md) and [ADR-013](013-ci-cd.md). Amends [ADR-007](007-distribution.md) and
[ADR-014](014-versioning.md): the package's version and dist-tags.

## Context

Smarter Chat had its own repository, `smarter-sh/smarter-chat`, which the platform's `make react-install` cloned into
its React workspace, an ignored folder (ADR-003). Every change to the chat api contract was a change in two
repositories: the platform's Pydantic models, and this package's schema and generated types. The clone was a step in
the platform's make targets, CI and React build. The package had its own version line (0.x up to 0.16.2), its own
semantic-release, CI and release workflows (ADR-013), its own copies of the pre-commit, commitlint and Codecov
configuration, and a developer could have two working trees of it that drifted apart. Since ADR-019, the web
console's workbench, the package's main consumer, is the platform's own app.

## Decision

Smarter Chat is a package of the platform's React workspace, committed in the platform's repository, in
`smarter/react/packages/smarter.sh-chat`. The folder is named after the npm scope, `@smarter.sh`, like the workspace's
other published package, `@smarter.sh/ui-widgets` (`smarter.sh-widgets`), so that the two stand apart from the
private `@smarter/*` console apps. `smarter-sh/smarter-chat` is archived; it keeps the package's history up to
0.16.2, as does this folder's `CHANGELOG.md`.

- **One change, one commit.** A change to the contract, or to the workbench that hosts the chat, is made with the
  chat's side in the same commit. `make chat-contract` regenerates `contract/` and `src/contract.gen.ts` in place.
- **The platform's tooling.** The platform's pre-commit hooks, commitlint, Codecov and CI cover the package. Its own
  copies of that configuration, its Makefile and its standalone community files are gone. It keeps the configuration
  that its two builds and its tests need on their own: `vite.config.ts`, `vitest.config.ts`, `test/`, `.storybook/`,
  `eslint.config.js` and the tsconfigs.
- **Releases.** The platform's `.github/workflows/uiChatRelease.yml` publishes the package with each platform
  release, which semantic-release makes from the platform's conventional commits. The package's version is the
  platform's (0.36.0 and later), set from the release's tag before the build, so that the embed script reports it
  (`window.SmarterChat.version`). It isn't committed: the workspace's copy is the platform's placeholder,
  `9999.9999.9999.dev9999`, which the workbench's dependency, `*`, accepts.
- **Dist-tags.** A release from `main` is published with `latest`, one from another branch, such as `next`, with
  `next`, and the `alpha` and `beta` prereleases with `alpha` and `beta`. jsDelivr's ranges (`@0`, `@0.36`) follow
  only `latest`, and are refreshed after each one, as before (ADR-007). Publishing still uses npm's trusted publishing,
  now from the platform's repository, with a provenance statement that names it.

## Alternatives Considered

- **Keep the separate repository.** It suited a package that the platform consumed from a CDN. Once the workbench was
  the platform's own app (ADR-019), the separation only added the two-repository changes and the clone.
- **Move it with its history** (`git subtree`). The archived repository keeps the history, and is linked from the
  package's README and its developer guide.
- **Keep its own version line**, with semantic-release configured for one folder of the repository. Every platform
  release now publishes the package, whether or not the chat changed, which is harmless, and one release process
  covers both published packages.

## Consequences

- **Positive:**
  - Contract and workbench changes land, and are tested, together.
  - No clone step, and one copy of the tooling.
  - The integrations can pin a version that matches the platform release they were tested with.
- **Negative:**
  - The version jumps from 0.16 to 0.36. Sites pinned to `@0.16` stay on 0.16.2; sites on `@0` follow the new versions.
  - A new version is published with every platform release, even when the chat didn't change.
  - Some ADRs, such as [ADR-002](002-three-builds.md), [ADR-012](012-testing.md) and [ADR-015](015-code-quality.md),
    still mention the old `make` targets or the separate repository in passing. Where they do, this ADR applies.
