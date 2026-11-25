# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.48.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.2...v0.48.3-alpha.1) (2026-11-25)

### Bug Fixes

* **account:** log users by id, not username, on sign-in and User saves ([2154890](https://github.com/smarter-sh/smarter/commit/2154890d6125da358f51575f4c0b9cd4f64068fa)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1055](https://github.com/smarter-sh/smarter/issues/1055) [#1055](https://github.com/smarter-sh/smarter/issues/1055)
* **helm:** default the image to mcdaniel0073/smarter on docker hub ([3b1d771](https://github.com/smarter-sh/smarter/commit/3b1d7711526999b5e76cc78dcff0a4cc7c8cce80))

## [0.48.2](https://github.com/smarter-sh/smarter/compare/v0.48.1...v0.48.2) (2026-11-25)

### Bug Fixes

- **helm:** run mariadb, redis and loki on the stateful node pool ([19cc09c](https://github.com/smarter-sh/smarter/commit/19cc09c7cbdf214721052ffb6a11f95ba36cd9b0)), closes [#942](https://github.com/smarter-sh/smarter/issues/942) [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#929](https://github.com/smarter-sh/smarter/issues/929) [#931](https://github.com/smarter-sh/smarter/issues/931)

## [0.48.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.1...v0.48.2-alpha.1) (2026-11-25)

### Bug Fixes

- **helm:** run mariadb, redis and loki on the stateful node pool ([19cc09c](https://github.com/smarter-sh/smarter/commit/19cc09c7cbdf214721052ffb6a11f95ba36cd9b0)), closes [#942](https://github.com/smarter-sh/smarter/issues/942) [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#929](https://github.com/smarter-sh/smarter/issues/929) [#931](https://github.com/smarter-sh/smarter/issues/931)

## [0.48.1](https://github.com/smarter-sh/smarter/compare/v0.48.0...v0.48.1) (2026-11-25)

### Bug Fixes

- **account:** add a Tutorials row to the welcome email ([414fb59](https://github.com/smarter-sh/smarter/commit/414fb59182ae2b188f1c34f5c00457e143c8f66e))
- **account:** link the welcome email's video to YouTube ([b7b594c](https://github.com/smarter-sh/smarter/commit/b7b594cb15ae52973fc3f701bf723c71b917012c))
- **cache:** bump cache-results to 0.2.2 to survive redis outages ([dde5f84](https://github.com/smarter-sh/smarter/commit/dde5f84abc95aadbd7b911c9be9841ba4c9293c6)), closes [smarter-sh/cache-results#11](https://github.com/smarter-sh/cache-results/issues/11) [#941](https://github.com/smarter-sh/smarter/issues/941)

### Refactoring

- **helm:** rename the api's values key from app to api ([0ccf00b](https://github.com/smarter-sh/smarter/commit/0ccf00bff881e64cfc0eb2b59f4d97b3e0ee771a))

## [0.48.1-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.48.1-alpha.2...v0.48.1-alpha.3) (2026-11-24)

### Bug Fixes

- **cache:** bump cache-results to 0.2.2 to survive redis outages ([dde5f84](https://github.com/smarter-sh/smarter/commit/dde5f84abc95aadbd7b911c9be9841ba4c9293c6)), closes [smarter-sh/cache-results#11](https://github.com/smarter-sh/cache-results/issues/11) [#941](https://github.com/smarter-sh/smarter/issues/941)

### Refactoring

- **helm:** rename the api's values key from app to api ([0ccf00b](https://github.com/smarter-sh/smarter/commit/0ccf00bff881e64cfc0eb2b59f4d97b3e0ee771a))

## [0.48.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.1-alpha.1...v0.48.1-alpha.2) (2026-11-24)

### Bug Fixes

- **account:** add a Tutorials row to the welcome email ([414fb59](https://github.com/smarter-sh/smarter/commit/414fb59182ae2b188f1c34f5c00457e143c8f66e))

## [0.48.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.0...v0.48.1-alpha.1) (2026-11-24)

### Bug Fixes

- **account:** link the welcome email's video to YouTube ([b7b594c](https://github.com/smarter-sh/smarter/commit/b7b594cb15ae52973fc3f701bf723c71b917012c))

## [0.48.0](https://github.com/smarter-sh/smarter/compare/v0.47.6...v0.48.0) (2026-11-24)

### Features

- **account:** batch apply GitHub repositories, and check LLM prices ([f6fa0bf](https://github.com/smarter-sh/smarter/commit/f6fa0bf3aeb6bd94374246d48a01364b0aab5b0a))
- **doodle:** email new drawings; serve the newest, and any one doodle ([38d9b31](https://github.com/smarter-sh/smarter/commit/38d9b3105eb90002445c17662b4c514bdad9cbff))

### Bug Fixes

- **docs:** list every page in the sitemap after an incremental build ([f60aec0](https://github.com/smarter-sh/smarter/commit/f60aec0b894a42f68725e087a538e5f62c74916b))
- **settings:** indent the startup environment log by two spaces ([ed6f71f](https://github.com/smarter-sh/smarter/commit/ed6f71f5b93791be8f218ccf8a55e14cdf72181d))

## [0.48.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.7-alpha.1...v0.48.0-alpha.1) (2026-11-24)

### Features

- **account:** batch apply GitHub repositories, and check LLM prices ([f6fa0bf](https://github.com/smarter-sh/smarter/commit/f6fa0bf3aeb6bd94374246d48a01364b0aab5b0a))
- **doodle:** email new drawings; serve the newest, and any one doodle ([38d9b31](https://github.com/smarter-sh/smarter/commit/38d9b3105eb90002445c17662b4c514bdad9cbff))
