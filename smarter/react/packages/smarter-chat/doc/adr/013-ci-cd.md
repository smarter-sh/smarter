# ADR-013: CI/CD and Releases

## Status

Accepted

Follows the platform's [ADR-014: CI/CD](https://github.com/smarter-sh/smarter/blob/main/docs/source/adr/014-ci-cd.rst): the same branches, semantic-release configuration and merge-back.

## Context

Five platform integrations, and every hand-written tag, load the embed script from npm through jsDelivr (ADR-007). A version that is tagged on GitHub, but not on npm, is a 404 on their sites. A release must be built from its tag, tested, and checked as it will be published.

## Decision

GitHub Actions only:

- **`test.yml`**, on every push to `main` and `alpha` and every pull request: Prettier, ESLint, TypeScript, and the tests with coverage, uploaded to Codecov.
- **`build.yml`**, on every push to `main`, `alpha` and `beta` and every pull request: builds the app, the library and the embed script, runs `check:dist`, and keeps the packed tarball as an artifact for 14 days, so a change can be installed in another repository before it is released.
- **`pushMain.yml`**: semantic-release on `main`, `beta` and `alpha` (prereleases). It writes the version to `package.json` and `CHANGELOG.md`, tags, and creates a GitHub release, but doesn't publish (`npmPublish: false`). A release on `main` is merged back into `alpha`.
- **`release.yml`**, on a published GitHub release (or by hand, for a tag): checks out the tag, fails if it isn't `package.json`'s version, runs the tests, builds and checks, and publishes that same `dist/` with npm's trusted publishing, `--provenance`, and the `latest` dist-tag (ADR-007). It runs only for releases from `main`: it skips prereleases and runs started from another branch, and fails for a tag that isn't on `main`. It runs in the `npm` environment, which can require a reviewer.
- Both build workflows use one composite action, `.github/actions/build-package`.
- semantic-release authenticates with the `PAT` secret, not `GITHUB_TOKEN`, so that the release it creates triggers `release.yml`.
- **Release commits don't carry `[skip ci]`.** If `main` is fast-forwarded to `alpha`'s head, and that head is a release commit, GitHub would skip `pushMain.yml`, and `main` would never be released. Without the marker, a release commit's own push runs semantic-release again, which finds nothing to release.
- `make release` remains a manual fallback.

## Alternatives Considered

- **semantic-release publishing to npm itself.** It would need an npm token in the repository, and would publish a `dist/` that was never checked.
- **Publishing by hand.** 0.9.0 showed that a step that isn't automated gets missed.

## Consequences

- **Positive:**
  - Every release is tested, checked and on npm, with provenance, minutes after its commit reaches a release branch.
- **Negative:**
  - Release commits, and the weekly pre-commit version bumps, run every workflow, as no-ops for the release.
  - Trusted publishing must be configured once on npmjs.com, for this repository, `release.yml` and the `npm` environment.

## Related ADRs

- [ADR-007: Distribution: npm and jsDelivr](007-distribution.md)
- [ADR-012: Testing](012-testing.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
