# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.48.2](https://github.com/smarter-sh/smarter/compare/v0.48.1...v0.48.2) (2026-11-25)

### Bug Fixes

* **helm:** run mariadb, redis and loki on the stateful node pool ([19cc09c](https://github.com/smarter-sh/smarter/commit/19cc09c7cbdf214721052ffb6a11f95ba36cd9b0)), closes [#942](https://github.com/smarter-sh/smarter/issues/942) [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#929](https://github.com/smarter-sh/smarter/issues/929) [#931](https://github.com/smarter-sh/smarter/issues/931)

## [0.48.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.1...v0.48.2-alpha.1) (2026-11-25)

### Bug Fixes

* **helm:** run mariadb, redis and loki on the stateful node pool ([19cc09c](https://github.com/smarter-sh/smarter/commit/19cc09c7cbdf214721052ffb6a11f95ba36cd9b0)), closes [#942](https://github.com/smarter-sh/smarter/issues/942) [#1052](https://github.com/smarter-sh/smarter/issues/1052) [#929](https://github.com/smarter-sh/smarter/issues/929) [#931](https://github.com/smarter-sh/smarter/issues/931)

## [0.48.1](https://github.com/smarter-sh/smarter/compare/v0.48.0...v0.48.1) (2026-11-25)

### Bug Fixes

* **account:** add a Tutorials row to the welcome email ([414fb59](https://github.com/smarter-sh/smarter/commit/414fb59182ae2b188f1c34f5c00457e143c8f66e))
* **account:** link the welcome email's video to YouTube ([b7b594c](https://github.com/smarter-sh/smarter/commit/b7b594cb15ae52973fc3f701bf723c71b917012c))
* **cache:** bump cache-results to 0.2.2 to survive redis outages ([dde5f84](https://github.com/smarter-sh/smarter/commit/dde5f84abc95aadbd7b911c9be9841ba4c9293c6)), closes [smarter-sh/cache-results#11](https://github.com/smarter-sh/cache-results/issues/11) [#941](https://github.com/smarter-sh/smarter/issues/941)

### Refactoring

* **helm:** rename the api's values key from app to api ([0ccf00b](https://github.com/smarter-sh/smarter/commit/0ccf00bff881e64cfc0eb2b59f4d97b3e0ee771a))

## [0.48.1-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.48.1-alpha.2...v0.48.1-alpha.3) (2026-11-24)

### Bug Fixes

* **cache:** bump cache-results to 0.2.2 to survive redis outages ([dde5f84](https://github.com/smarter-sh/smarter/commit/dde5f84abc95aadbd7b911c9be9841ba4c9293c6)), closes [smarter-sh/cache-results#11](https://github.com/smarter-sh/cache-results/issues/11) [#941](https://github.com/smarter-sh/smarter/issues/941)

### Refactoring

* **helm:** rename the api's values key from app to api ([0ccf00b](https://github.com/smarter-sh/smarter/commit/0ccf00bff881e64cfc0eb2b59f4d97b3e0ee771a))

## [0.48.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.1-alpha.1...v0.48.1-alpha.2) (2026-11-24)

### Bug Fixes

* **account:** add a Tutorials row to the welcome email ([414fb59](https://github.com/smarter-sh/smarter/commit/414fb59182ae2b188f1c34f5c00457e143c8f66e))

## [0.48.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.0...v0.48.1-alpha.1) (2026-11-24)

### Bug Fixes

* **account:** link the welcome email's video to YouTube ([b7b594c](https://github.com/smarter-sh/smarter/commit/b7b594cb15ae52973fc3f701bf723c71b917012c))

## [0.48.0](https://github.com/smarter-sh/smarter/compare/v0.47.6...v0.48.0) (2026-11-24)

### Features

* **account:** batch apply GitHub repositories, and check LLM prices ([f6fa0bf](https://github.com/smarter-sh/smarter/commit/f6fa0bf3aeb6bd94374246d48a01364b0aab5b0a))
* **doodle:** email new drawings; serve the newest, and any one doodle ([38d9b31](https://github.com/smarter-sh/smarter/commit/38d9b3105eb90002445c17662b4c514bdad9cbff))

### Bug Fixes

* **docs:** list every page in the sitemap after an incremental build ([f60aec0](https://github.com/smarter-sh/smarter/commit/f60aec0b894a42f68725e087a538e5f62c74916b))
* **settings:** indent the startup environment log by two spaces ([ed6f71f](https://github.com/smarter-sh/smarter/commit/ed6f71f5b93791be8f218ccf8a55e14cdf72181d))

## [0.48.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.7-alpha.1...v0.48.0-alpha.1) (2026-11-24)

### Features

* **account:** batch apply GitHub repositories, and check LLM prices ([f6fa0bf](https://github.com/smarter-sh/smarter/commit/f6fa0bf3aeb6bd94374246d48a01364b0aab5b0a))
* **doodle:** email new drawings; serve the newest, and any one doodle ([38d9b31](https://github.com/smarter-sh/smarter/commit/38d9b3105eb90002445c17662b4c514bdad9cbff))

## [0.47.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.6...v0.47.7-alpha.1) (2026-11-23)

### Bug Fixes

* **docs:** list every page in the sitemap after an incremental build ([f60aec0](https://github.com/smarter-sh/smarter/commit/f60aec0b894a42f68725e087a538e5f62c74916b))
* **settings:** indent the startup environment log by two spaces ([ed6f71f](https://github.com/smarter-sh/smarter/commit/ed6f71f5b93791be8f218ccf8a55e14cdf72181d))

## [0.47.6](https://github.com/smarter-sh/smarter/compare/v0.47.5...v0.47.6) (2026-11-23)

### Bug Fixes

* **llmclient:** charge workbench prompts to the user who sends them ([2fad7e5](https://github.com/smarter-sh/smarter/commit/2fad7e5f0468e5f5e5df5dcd7e20ef65888d0c77))

## [0.47.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.5...v0.47.6-alpha.1) (2026-11-23)

### Bug Fixes

* **llmclient:** charge workbench prompts to the user who sends them ([2fad7e5](https://github.com/smarter-sh/smarter/commit/2fad7e5f0468e5f5e5df5dcd7e20ef65888d0c77))

## [0.47.5](https://github.com/smarter-sh/smarter/compare/v0.47.4...v0.47.5) (2026-11-23)

### Bug Fixes

* **journal:** keep the Smarter Journal on by default ([f5ca995](https://github.com/smarter-sh/smarter/commit/f5ca9950b7b2a08f23a547f844d24e4fc93eaeaa))
* **mcpserver:** lock the index's row before store_files() replaces its files ([125578f](https://github.com/smarter-sh/smarter/commit/125578f1655d3e14763cbbc1376f798dc6c336f2)), closes [#1046](https://github.com/smarter-sh/smarter/issues/1046)

## [0.47.5-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.47.5-alpha.1...v0.47.5-alpha.2) (2026-11-23)

### Bug Fixes

* **mcpserver:** lock the index's row before store_files() replaces its files ([125578f](https://github.com/smarter-sh/smarter/commit/125578f1655d3e14763cbbc1376f798dc6c336f2)), closes [#1046](https://github.com/smarter-sh/smarter/issues/1046)

## [0.47.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.4...v0.47.5-alpha.1) (2026-11-23)

### Bug Fixes

* **journal:** keep the Smarter Journal on by default ([f5ca995](https://github.com/smarter-sh/smarter/commit/f5ca9950b7b2a08f23a547f844d24e4fc93eaeaa))

## [0.47.4](https://github.com/smarter-sh/smarter/compare/v0.47.3...v0.47.4) (2026-11-23)

### Bug Fixes

* **account:** refuse a budget limit that isn't to the cent ([dc73c8c](https://github.com/smarter-sh/smarter/commit/dc73c8cac1936ca2f7c1d6b944c81f659bf8b382))
* **account:** say a budget's daily limit, not its dayly limit ([3444806](https://github.com/smarter-sh/smarter/commit/34448067c5778da4f88482fff6bfbd9f238a8b79))
* **account:** start every platform with its default models' prices ([6c071a5](https://github.com/smarter-sh/smarter/commit/6c071a5377e35c9c026f1de83d11ff21d51d7a85))
* **provider:** charge a model call's tokens once per resource ([961a552](https://github.com/smarter-sh/smarter/commit/961a552798f748175ed5e0127c90c9bfcc00ec31))

## [0.47.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.3...v0.47.4-alpha.1) (2026-11-23)

### Bug Fixes

* **account:** refuse a budget limit that isn't to the cent ([dc73c8c](https://github.com/smarter-sh/smarter/commit/dc73c8cac1936ca2f7c1d6b944c81f659bf8b382))
* **account:** say a budget's daily limit, not its dayly limit ([3444806](https://github.com/smarter-sh/smarter/commit/34448067c5778da4f88482fff6bfbd9f238a8b79))
* **account:** start every platform with its default models' prices ([6c071a5](https://github.com/smarter-sh/smarter/commit/6c071a5377e35c9c026f1de83d11ff21d51d7a85))
* **provider:** charge a model call's tokens once per resource ([961a552](https://github.com/smarter-sh/smarter/commit/961a552798f748175ed5e0127c90c9bfcc00ec31))

## [0.47.3](https://github.com/smarter-sh/smarter/compare/v0.47.2...v0.47.3) (2026-11-23)

### Bug Fixes

* **llmclient:** keep a deployed llmclient deployed when it is applied ([beebdba](https://github.com/smarter-sh/smarter/commit/beebdbab78d9afd3fb52200f0edf898971a8c041))
* **llmclient:** report a local platform's deployed url on localhost ([9dbf87d](https://github.com/smarter-sh/smarter/commit/9dbf87da3f9b66ca23024d9970e743acff5b595b))

## [0.47.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.47.2...v0.47.3-alpha.1) (2026-11-23)

### Bug Fixes

* **llmclient:** keep a deployed llmclient deployed when it is applied ([beebdba](https://github.com/smarter-sh/smarter/commit/beebdbab78d9afd3fb52200f0edf898971a8c041))
* **llmclient:** report a local platform's deployed url on localhost ([9dbf87d](https://github.com/smarter-sh/smarter/commit/9dbf87da3f9b66ca23024d9970e743acff5b595b))

## [0.47.2](https://github.com/smarter-sh/smarter/compare/v0.47.1...v0.47.2) (2026-11-23)

### Bug Fixes

* **account:** skip the files that a repository's .smarterignore lists ([82f4973](https://github.com/smarter-sh/smarter/commit/82f4973a199861be163eed36e3894fe2970a7ae5))
* bump smarter-console to v1.1.15 ([c1aa6c3](https://github.com/smarter-sh/smarter/commit/c1aa6c31404b2e4fd4ffea1c844babd53776d4a3))
* **vectorstore:** add the cli api's documents command ([de9f828](https://github.com/smarter-sh/smarter/commit/de9f8287a7db9db8ed6e408ccf51a56c7c631f83))
* **vectorstore:** queue waiting documents when a deploy is ready ([1416e42](https://github.com/smarter-sh/smarter/commit/1416e42f0c399b118615adfd6c4faad0bf91b198))

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
