# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.47.2-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.47.2-alpha.2...v0.47.2-alpha.3) (2026-11-23)

### Bug Fixes

* bump smarter-console to v1.1.15 ([c1aa6c3](https://github.com/smarter-sh/smarter/commit/c1aa6c31404b2e4fd4ffea1c844babd53776d4a3))

## [0.47.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.47.2-alpha.1...v0.47.2-alpha.2) (2026-11-23)

### Bug Fixes

* **account:** skip the files that a repository's .smarterignore lists ([82f4973](https://github.com/smarter-sh/smarter/commit/82f4973a199861be163eed36e3894fe2970a7ae5))
* **vectorstore:** add the cli api's documents command ([de9f828](https://github.com/smarter-sh/smarter/commit/de9f8287a7db9db8ed6e408ccf51a56c7c631f83))

## [0.47.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.1...v0.47.2-alpha.1) (2026-11-23)

### Bug Fixes

- **vectorstore:** queue waiting documents when a deploy is ready ([1416e42](https://github.com/smarter-sh/smarter/commit/1416e42f0c399b118615adfd6c4faad0bf91b198))

## [0.47.1](https://github.com/smarter-sh/smarter/compare/v0.47.0...v0.47.1) (2026-11-23)

### Bug Fixes

- **vectorstore:** deploy in a retrying Celery task, with conditions ([2f775ba](https://github.com/smarter-sh/smarter/commit/2f775ba9f64729db6a3f4fea63f62a6837f07a90))

## [0.47.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.0...v0.47.1-alpha.1) (2026-11-23)

### Bug Fixes

- **vectorstore:** deploy in a retrying Celery task, with conditions ([2f775ba](https://github.com/smarter-sh/smarter/commit/2f775ba9f64729db6a3f4fea63f62a6837f07a90))

## [0.47.0](https://github.com/smarter-sh/smarter/compare/v0.46.20...v0.47.0) (2026-11-23)

### Features

- **vectorsearch:** let an LLMClient search its documents as a tool ([9718adf](https://github.com/smarter-sh/smarter/commit/9718adfdd74807e8efbfecf68af94b974b8f3b75))

### Bug Fixes

- **settings:** log the last four characters of secret settings ([69eeae7](https://github.com/smarter-sh/smarter/commit/69eeae7740dd3a1ec22a4645f6f9751c05d75d65))
- **startup:** show DRF and Pydantic versions on the startup banner ([a41a680](https://github.com/smarter-sh/smarter/commit/a41a680a24072cb3adcf61cffdba70d219f349bd))
- **vectorstore:** fail a deploy whose database can't be reached ([3e0a416](https://github.com/smarter-sh/smarter/commit/3e0a4160f85daffcf762290d3b7704a765c293f2))

## [0.47.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.21-alpha.1...v0.47.0-alpha.1) (2026-11-23)

### Features

- **vectorsearch:** let an LLMClient search its documents as a tool ([9718adf](https://github.com/smarter-sh/smarter/commit/9718adfdd74807e8efbfecf68af94b974b8f3b75))

### Bug Fixes

- **vectorstore:** fail a deploy whose database can't be reached ([3e0a416](https://github.com/smarter-sh/smarter/commit/3e0a4160f85daffcf762290d3b7704a765c293f2))
