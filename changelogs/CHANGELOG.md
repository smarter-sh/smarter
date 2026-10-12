# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.21.0](https://github.com/smarter-sh/smarter/compare/v0.20.5...v0.21.0) (2026-10-12)

### Features

* **llmclient:** split spec.config into prompt and styles ([38fc728](https://github.com/smarter-sh/smarter/commit/38fc72864ccdf3c6cdb68f400795a164c9b50fda))

### Bug Fixes

* **llmclient:** journal undeploy, document smarter on kubernetes ([194071f](https://github.com/smarter-sh/smarter/commit/194071f552250a454b360b9598c37cd5c346abc7))
* remove import-time celery broker probe, fix sphinx doc warnings ([bacab74](https://github.com/smarter-sh/smarter/commit/bacab740773b8733bb890af8f4babf81982895a7))

### Refactoring

* **react:** model vite manifest.json and assets with pydantic ([a478e0b](https://github.com/smarter-sh/smarter/commit/a478e0b86e53ab9ffc29d71f14987356793f8370))

## [0.21.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.21.0-alpha.1...v0.21.0-alpha.2) (2026-10-12)

### Bug Fixes

* **llmclient:** journal undeploy, document smarter on kubernetes ([194071f](https://github.com/smarter-sh/smarter/commit/194071f552250a454b360b9598c37cd5c346abc7))

## [0.21.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.20.5...v0.21.0-alpha.1) (2026-10-12)

### Features

* **llmclient:** split spec.config into prompt and styles ([38fc728](https://github.com/smarter-sh/smarter/commit/38fc72864ccdf3c6cdb68f400795a164c9b50fda))

### Bug Fixes

* remove import-time celery broker probe, fix sphinx doc warnings ([bacab74](https://github.com/smarter-sh/smarter/commit/bacab740773b8733bb890af8f4babf81982895a7))

### Refactoring

* **react:** model vite manifest.json and assets with pydantic ([a478e0b](https://github.com/smarter-sh/smarter/commit/a478e0b86e53ab9ffc29d71f14987356793f8370))

## [0.20.5](https://github.com/smarter-sh/smarter/compare/v0.20.4...v0.20.5) (2026-10-12)

### Bug Fixes

* **prompt:** pin contract schema ids to smarter.sh, not root_domain ([b3ea974](https://github.com/smarter-sh/smarter/commit/b3ea9743e28c8de30ae824833ec23f3bbd5523ef))

## [0.20.4](https://github.com/smarter-sh/smarter/compare/v0.20.3...v0.20.4) (2026-10-12)

### Bug Fixes

* **account:** create the platform admin as a superuser in one insert ([4a73fe2](https://github.com/smarter-sh/smarter/commit/4a73fe248ba902bf5fcb3794a7d7e78467ffee03))

## [0.20.3](https://github.com/smarter-sh/smarter/compare/v0.20.2...v0.20.3) (2026-10-12)

### Bug Fixes

* **account:** refresh cached UserProfiles when their User is saved ([e1ae6bd](https://github.com/smarter-sh/smarter/commit/e1ae6bd6c19f42ca5abe41fd936e3579e5d05dfd))
* **account:** stop caching an empty profile list for new users ([6c44094](https://github.com/smarter-sh/smarter/commit/6c4409409f1e9156e910027a7023684b365fd288))
* **journal:** shore up mvp with contract, api and signals ([d7422f4](https://github.com/smarter-sh/smarter/commit/d7422f41d5fbfaee7337c0675bbdaf1766df8b5a))
* make dunder methods consistent and add missing ones ([1a68c85](https://github.com/smarter-sh/smarter/commit/1a68c854064de0f97ac57412bc764fd4c66cf0b5))

### Performance

* **account:** stop per-request cache churn, cache hot ORM lookups ([fdefcae](https://github.com/smarter-sh/smarter/commit/fdefcae1471d4216a86fbe56955a1d2b68aba99a))

## [0.20.3-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.20.3-alpha.4...v0.20.3-alpha.5) (2026-10-12)

### Bug Fixes

* **account:** stop caching an empty profile list for new users ([6c44094](https://github.com/smarter-sh/smarter/commit/6c4409409f1e9156e910027a7023684b365fd288))

## [0.20.3-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.20.3-alpha.3...v0.20.3-alpha.4) (2026-10-11)

### Bug Fixes

* **account:** refresh cached UserProfiles when their User is saved ([e1ae6bd](https://github.com/smarter-sh/smarter/commit/e1ae6bd6c19f42ca5abe41fd936e3579e5d05dfd))

## [0.20.3-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.20.3-alpha.2...v0.20.3-alpha.3) (2026-10-11)

### Bug Fixes

* make dunder methods consistent and add missing ones ([1a68c85](https://github.com/smarter-sh/smarter/commit/1a68c854064de0f97ac57412bc764fd4c66cf0b5))

## [0.20.3-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.20.3-alpha.1...v0.20.3-alpha.2) (2026-10-11)

### Bug Fixes

* **journal:** shore up mvp with contract, api and signals ([d7422f4](https://github.com/smarter-sh/smarter/commit/d7422f41d5fbfaee7337c0675bbdaf1766df8b5a))

## [0.20.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.20.2...v0.20.3-alpha.1) (2026-10-11)

### Performance

* **account:** stop per-request cache churn, cache hot ORM lookups ([fdefcae](https://github.com/smarter-sh/smarter/commit/fdefcae1471d4216a86fbe56955a1d2b68aba99a))

## [0.20.2](https://github.com/smarter-sh/smarter/compare/v0.20.1...v0.20.2) (2026-10-11)

### Bug Fixes

* **cache:** correct caching design mistakes in plugins and mcpclient ([eeb7a7a](https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48))
* **prompt:** enforce the chat api contract with pydantic models ([0630dcb](https://github.com/smarter-sh/smarter/commit/0630dcb55ff54f81bae9ce3c3b62e55331c2203a))

### Refactoring

* **typing:** add SmarterDictType and replace improper uses of Any ([bcd679a](https://github.com/smarter-sh/smarter/commit/bcd679acdd4859faa70aa7defcc20386ce14bd3e))

## [0.20.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.20.2-alpha.1...v0.20.2-alpha.2) (2026-10-11)

### Bug Fixes

* **prompt:** enforce the chat api contract with pydantic models ([0630dcb](https://github.com/smarter-sh/smarter/commit/0630dcb55ff54f81bae9ce3c3b62e55331c2203a))

## [0.20.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.20.1...v0.20.2-alpha.1) (2026-10-11)

### Bug Fixes

* **cache:** correct caching design mistakes in plugins and mcpclient ([eeb7a7a](https://github.com/smarter-sh/smarter/commit/eeb7a7a19bccd08c0b341feecf3ca444875a1f48))

## [0.20.1](https://github.com/smarter-sh/smarter/compare/v0.20.0...v0.20.1) (2026-10-10)

### Bug Fixes

* build the Docker image on the python 3.14 base image ([690f42c](https://github.com/smarter-sh/smarter/commit/690f42c5fb68884b106245f7e745b967248a727b))

## [0.20.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.20.0...v0.20.1-alpha.1) (2026-10-10)

### Bug Fixes

* build the Docker image on the python 3.14 base image ([690f42c](https://github.com/smarter-sh/smarter/commit/690f42c5fb68884b106245f7e745b967248a727b))

## [0.20.0](https://github.com/smarter-sh/smarter/compare/v0.19.0...v0.20.0) (2026-10-10)

### Features

- python3.14 upgrade ([f2ac55c](https://github.com/smarter-sh/smarter/commit/f2ac55cbea2351c67be0e26bab78e048316b6108))

### Bug Fixes

- **account:** sync infrastructure inventory in initialize_platform ([2350312](https://github.com/smarter-sh/smarter/commit/235031256a9d75631dbfdd2cb568d4c18743b95f))

## [0.20.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.19.1-alpha.1...v0.20.0-alpha.1) (2026-10-10)

### Features

- python3.14 upgrade ([f2ac55c](https://github.com/smarter-sh/smarter/commit/f2ac55cbea2351c67be0e26bab78e048316b6108))
