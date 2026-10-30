# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.38.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.38.0-alpha.3...v0.38.0-alpha.4) (2026-10-30)

### Bug Fixes

* **api:** add detailUrl to the remaining REST api contract models ([4ca5156](https://github.com/smarter-sh/smarter/commit/4ca5156f3cbe9859383f34ce8c3c9f0511de5a71))
* **dashboard:** open global search results in the resource's detail ([a125477](https://github.com/smarter-sh/smarter/commit/a125477103fa4c96e2b632ecb600ec33632cdf55))
* **react:** redesign the resource detail's fields and its source code ([9e5992d](https://github.com/smarter-sh/smarter/commit/9e5992d4b9c3e6fc15a8eaca234bea2ff4e73ddb))

## [0.38.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.38.0-alpha.2...v0.38.0-alpha.3) (2026-10-30)

### Bug Fixes

* **dashboard:** highlight the sidebar item of the page on the server ([13d3b8f](https://github.com/smarter-sh/smarter/commit/13d3b8f3e3f5a56669e4fe76afdf57df437b9d6d))
* **llmclient:** log rejected scanner requests as warnings, not errors ([3c7c246](https://github.com/smarter-sh/smarter/commit/3c7c24662356c641c95e5b23110253e49a045d34))
* **react:** open a tabbed resource detail when a list row is chosen ([0a347f3](https://github.com/smarter-sh/smarter/commit/0a347f3e3d05c10d01f6a38fedb311fd225295a4))

## [0.38.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.38.0-alpha.1...v0.38.0-alpha.2) (2026-10-30)

### Features

* **dashboard:** add global search; narrow lists by tag or annotation ([48abc37](https://github.com/smarter-sh/smarter/commit/48abc3722d3f8e14bbcd4f991f6ca88697c3fd99))

## [0.38.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.37.4-alpha.2...v0.38.0-alpha.1) (2026-10-30)

### Features

* **annotation:** store SAM annotations as Kubernetes-style rows ([cf82960](https://github.com/smarter-sh/smarter/commit/cf829605a2a7e5c6c747d4ea7b5cc3bb0283b3a5))

## [0.37.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.37.4-alpha.1...v0.37.4-alpha.2) (2026-10-30)

### Bug Fixes

* **prompt:** give prompts their own thread pool; drop unused settings ([ecc5b2d](https://github.com/smarter-sh/smarter/commit/ecc5b2de9311a5e1901afdeb7d12b1d17b18e0e0))

## [0.37.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.37.3...v0.37.4-alpha.1) (2026-10-30)

### Bug Fixes

* **console:** add a cookie notice with a link to the privacy policy ([0c5474e](https://github.com/smarter-sh/smarter/commit/0c5474e0ba5db00a24003d06734c693b49fc26ae))

## [0.37.3](https://github.com/smarter-sh/smarter/compare/v0.37.2...v0.37.3) (2026-10-30)

### Bug Fixes

* **django:** close the db connections that error pages leave open ([7559232](https://github.com/smarter-sh/smarter/commit/755923239019e32067c2dabaa76a1acdd6928f76))

## [0.37.2](https://github.com/smarter-sh/smarter/compare/v0.37.1...v0.37.2) (2026-10-28)

### Bug Fixes

* **console:** add a cookie notice with a link to the privacy policy ([0c5474e](https://github.com/smarter-sh/smarter/commit/0c5474e0ba5db00a24003d06734c693b49fc26ae))

## [0.37.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.37.1...v0.37.2-alpha.1) (2026-10-28)

### Bug Fixes

- **llmclient:** resolve a deployed host by its whole label ([98b7fdd](https://github.com/smarter-sh/smarter/commit/98b7fdd906ceb3b114fce3b06aafdfc67b6d4b43))

### Refactoring

- **cache:** log the tool call cache's misses ([89856d5](https://github.com/smarter-sh/smarter/commit/89856d58f5af340d8271e163d4914b19b28363dd))

### Performance

- drop per-request debug logging and redundant work ([406c571](https://github.com/smarter-sh/smarter/commit/406c571da9bac75ec41ba398f2267cc7a14a397b))

## [0.37.1](https://github.com/smarter-sh/smarter/compare/v0.37.0...v0.37.1) (2026-10-28)

### Bug Fixes

- **settings:** let prod's cors allow its own llmclient hosts ([e3c86ff](https://github.com/smarter-sh/smarter/commit/e3c86ff2aa2f02fc640d9a03a576f622eb00a21b))

### Performance

- **provider:** cache tool call results and first-message answers ([a504666](https://github.com/smarter-sh/smarter/commit/a504666eedbdde00873ebf357d65a8f9ecba369b))

## [0.37.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.37.0...v0.37.1-alpha.1) (2026-10-28)

### Bug Fixes

- **settings:** let prod's cors allow its own llmclient hosts ([e3c86ff](https://github.com/smarter-sh/smarter/commit/e3c86ff2aa2f02fc640d9a03a576f622eb00a21b))

### Performance

- **provider:** cache tool call results and first-message answers ([a504666](https://github.com/smarter-sh/smarter/commit/a504666eedbdde00873ebf357d65a8f9ecba369b))

## [0.37.0](https://github.com/smarter-sh/smarter/compare/v0.36.28...v0.37.0) (2026-10-28)

### Features

- **mcpserver:** search the blog, read every repo and manifest schemas ([e7bf450](https://github.com/smarter-sh/smarter/commit/e7bf45081d8149d9a56b44c652f50435d43b72e2))

## [0.37.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.36.28...v0.37.0-alpha.1) (2026-10-28)

### Features

- **mcpserver:** search the blog, read every repo and manifest schemas ([e7bf450](https://github.com/smarter-sh/smarter/commit/e7bf45081d8149d9a56b44c652f50435d43b72e2))
