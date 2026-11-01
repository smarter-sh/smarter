# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.40.4-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.40.4-alpha.2...v0.40.4-alpha.3) (2026-11-01)

### Bug Fixes

* **annotation:** invalidate cached annotations, prefetch them per page ([cb6bfcf](https://github.com/smarter-sh/smarter/commit/cb6bfcf818f3af8a86f1691006c81e5c71dc91d4))

## [0.40.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.40.4-alpha.1...v0.40.4-alpha.2) (2026-11-01)

### Bug Fixes

* **prompt:** redirect a signed-out visitor of the workbench to sign-in instead of a 403 ([5dd01b0](https://github.com/smarter-sh/smarter/commit/5dd01b0c47e12e3ebca7e208667bd35f967f2edb)), closes [#886](https://github.com/smarter-sh/smarter/issues/886)

## [0.40.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.3...v0.40.4-alpha.1) (2026-11-01)

### Bug Fixes

* **blog:** announce release posts in Slack [#announcements](https://github.com/smarter-sh/smarter/issues/announcements), not [#general](https://github.com/smarter-sh/smarter/issues/general) ([8be14ed](https://github.com/smarter-sh/smarter/commit/8be14edecaa8cf8f388e850fd4abb65c9ffb4eae))

## [0.40.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.2...v0.40.3-alpha.1) (2026-10-31)

### Bug Fixes

- **docker:** make code root-owned and pod filesystems read-only ([b94979d](https://github.com/smarter-sh/smarter/commit/b94979d63d2706bc9a1a847e9a42bb78fe4017b0))

## [0.40.2](https://github.com/smarter-sh/smarter/compare/v0.40.1...v0.40.2) (2026-10-31)

### Bug Fixes

- **account:** delete retired example resources at initialization ([6fc5bdc](https://github.com/smarter-sh/smarter/commit/6fc5bdc445fd7866c0e9dc6ca3c873fd1762b0be)), closes [#882](https://github.com/smarter-sh/smarter/issues/882)

## [0.40.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.1...v0.40.2-alpha.1) (2026-10-31)

### Bug Fixes

- **account:** delete retired example resources at initialization ([6fc5bdc](https://github.com/smarter-sh/smarter/commit/6fc5bdc445fd7866c0e9dc6ca3c873fd1762b0be)), closes [#882](https://github.com/smarter-sh/smarter/issues/882)

## [0.40.1](https://github.com/smarter-sh/smarter/compare/v0.40.0...v0.40.1) (2026-10-31)

### Bug Fixes

- **infrastructure:** post the init and backup job logs to Slack ([7d12824](https://github.com/smarter-sh/smarter/commit/7d12824f8830f876aeeae35edc379088068a72e6))

## [0.40.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.0...v0.40.1-alpha.1) (2026-10-31)

### Bug Fixes

- **infrastructure:** post the init and backup job logs to Slack ([7d12824](https://github.com/smarter-sh/smarter/commit/7d12824f8830f876aeeae35edc379088068a72e6))

## [0.40.0](https://github.com/smarter-sh/smarter/compare/v0.39.2...v0.40.0) (2026-10-31)

### Features

- **mcpserver:** add GitHub issue tools and manifest validation ([5a33702](https://github.com/smarter-sh/smarter/commit/5a33702b058a49fdb42b9b12673c62c2a1a02cc3))
- **mcpserver:** add pull request, issue reading and closing tools ([b70bd52](https://github.com/smarter-sh/smarter/commit/b70bd52bb5ba69d77aa2e37ab43880a478769277))

### Bug Fixes

- **middleware:** answer blocked paths 404, throttled clients 429 ([411e11b](https://github.com/smarter-sh/smarter/commit/411e11b4164ae78b8e4547316de51c17b6113f85))

## [0.40.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.40.0-alpha.1...v0.40.0-alpha.2) (2026-10-31)

### Features

- **mcpserver:** add pull request, issue reading and closing tools ([b70bd52](https://github.com/smarter-sh/smarter/commit/b70bd52bb5ba69d77aa2e37ab43880a478769277))

## [0.40.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.39.2...v0.40.0-alpha.1) (2026-10-31)

### Features

- **mcpserver:** add GitHub issue tools and manifest validation ([5a33702](https://github.com/smarter-sh/smarter/commit/5a33702b058a49fdb42b9b12673c62c2a1a02cc3))

### Bug Fixes

- **middleware:** answer blocked paths 404, throttled clients 429 ([411e11b](https://github.com/smarter-sh/smarter/commit/411e11b4164ae78b8e4547316de51c17b6113f85))
