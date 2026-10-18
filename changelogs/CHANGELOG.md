# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.33.5](https://github.com/smarter-sh/smarter/compare/v0.33.4...v0.33.5) (2026-10-18)

### Bug Fixes

* **logging:** keep the config api's chat session key in its request ([6f6636f](https://github.com/smarter-sh/smarter/commit/6f6636fe72bdf33e7eab4f33999287498bca01a1))
* **passthrough:** keep the server logs' scroll bars visible ([70f4cd7](https://github.com/smarter-sh/smarter/commit/70f4cd7cdeb9e987bc99315e8c4eed5a0d62fce9)), closes [#161a1](https://github.com/smarter-sh/smarter/issues/161a1) [#39424](https://github.com/smarter-sh/smarter/issues/39424) [#4a5663](https://github.com/smarter-sh/smarter/issues/4a5663)
* **prompt:** edit the llmclient manifest in the workbench console ([05f695e](https://github.com/smarter-sh/smarter/commit/05f695e747717b771c483cfb1bc0a432aa7d6f8d))
* **provider:** name plugins by their own names in tool messages ([e3f8ed1](https://github.com/smarter-sh/smarter/commit/e3f8ed1b9c2ec91f7f8c0c61c6580bdda1dbead8))

## [0.33.5-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.33.5-alpha.1...v0.33.5-alpha.2) (2026-10-18)

### Bug Fixes

* **logging:** keep the config api's chat session key in its request ([6f6636f](https://github.com/smarter-sh/smarter/commit/6f6636fe72bdf33e7eab4f33999287498bca01a1))
* **prompt:** edit the llmclient manifest in the workbench console ([05f695e](https://github.com/smarter-sh/smarter/commit/05f695e747717b771c483cfb1bc0a432aa7d6f8d))
* **provider:** name plugins by their own names in tool messages ([e3f8ed1](https://github.com/smarter-sh/smarter/commit/e3f8ed1b9c2ec91f7f8c0c61c6580bdda1dbead8))

## [0.33.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.33.4...v0.33.5-alpha.1) (2026-10-18)

### Bug Fixes

* **passthrough:** keep the server logs' scroll bars visible ([70f4cd7](https://github.com/smarter-sh/smarter/commit/70f4cd7cdeb9e987bc99315e8c4eed5a0d62fce9)), closes [#161a1](https://github.com/smarter-sh/smarter/issues/161a1) [#39424](https://github.com/smarter-sh/smarter/issues/39424) [#4a5663](https://github.com/smarter-sh/smarter/issues/4a5663)

## [0.33.4](https://github.com/smarter-sh/smarter/compare/v0.33.3...v0.33.4) (2026-10-18)

### Bug Fixes

* **llmtool:** add plugin request lifecycle signals, split signals pkg ([e2acf01](https://github.com/smarter-sh/smarter/commit/e2acf01748001c23d4caa69606764a9a946fd490))
* **logging:** stream each chat's own server logs, by session key ([a4f8af1](https://github.com/smarter-sh/smarter/commit/a4f8af1642018a4b9685d4d539da7ef59423c076))

## [0.33.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.33.4-alpha.1...v0.33.4-alpha.2) (2026-10-18)

### Bug Fixes

* **logging:** stream each chat's own server logs, by session key ([a4f8af1](https://github.com/smarter-sh/smarter/commit/a4f8af1642018a4b9685d4d539da7ef59423c076))

## [0.33.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.33.3...v0.33.4-alpha.1) (2026-10-18)

### Bug Fixes

* **llmtool:** add plugin request lifecycle signals, split signals pkg ([e2acf01](https://github.com/smarter-sh/smarter/commit/e2acf01748001c23d4caa69606764a9a946fd490))

## [0.33.3](https://github.com/smarter-sh/smarter/compare/v0.33.2...v0.33.3) (2026-10-18)

### Bug Fixes

* **llmclient:** deploy Stackademy LLMClients, drop the smarter example ([c6fda20](https://github.com/smarter-sh/smarter/commit/c6fda209f1a12322a87a154f98f4d68333c47523))
* **llmclient:** repair stackademy_api, make example data per app ([50c4ec8](https://github.com/smarter-sh/smarter/commit/50c4ec8fc1136fbec60ed072ef007fe191357aae))

### Refactoring

* **management:** base all add_example commands on one class ([a289f22](https://github.com/smarter-sh/smarter/commit/a289f22d870d973812e0378b48e5afdbf386a638))

## [0.33.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.33.2...v0.33.3-alpha.1) (2026-10-18)

### Bug Fixes

* **llmclient:** repair stackademy_api, make example data per app ([50c4ec8](https://github.com/smarter-sh/smarter/commit/50c4ec8fc1136fbec60ed072ef007fe191357aae))

### Refactoring

* **management:** base all add_example commands on one class ([a289f22](https://github.com/smarter-sh/smarter/commit/a289f22d870d973812e0378b48e5afdbf386a638))

## [0.33.2](https://github.com/smarter-sh/smarter/compare/v0.33.1...v0.33.2) (2026-10-17)

### Bug Fixes

* **console:** refactor the server logs window into a bash terminal ([1e17b3b](https://github.com/smarter-sh/smarter/commit/1e17b3b8b25fd6d952bce8bfbefbc8861b8267df))

## [0.33.1](https://github.com/smarter-sh/smarter/compare/v0.33.0...v0.33.1) (2026-10-17)

### Bug Fixes

- **passthrough:** show each prompt's server logs in a server logs tab ([c46eb29](https://github.com/smarter-sh/smarter/commit/c46eb29b21de1faf2afc4cad5bce949839fd45ed))

## [0.33.0](https://github.com/smarter-sh/smarter/compare/v0.32.2...v0.33.0) (2026-10-17)

### Features

- **console:** open extensions read-only to all, redesign passthrough ([c4724cc](https://github.com/smarter-sh/smarter/commit/c4724cceb9de796b2beb723ce9adeb1fedafb82f))
