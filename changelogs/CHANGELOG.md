# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.18.6](https://github.com/smarter-sh/smarter/compare/v0.18.5...v0.18.6) (2026-10-07)

### Bug Fixes

* **api:** restore legacy cli schema url and exempt schema calls from 404 throttle ([271a922](https://github.com/smarter-sh/smarter/commit/271a922ded5e58b3dbc2a1bcbcf4b19d02b5989d))
* **plugin:** stop tests from deleting the stackademy plugins' data ([7bfd5e7](https://github.com/smarter-sh/smarter/commit/7bfd5e78f4ecd0ea7cafb5c320a17cce36c8a0a8))

### Refactoring

* **react:** host smarter-chat locally, drop the react cdn scheme ([049c444](https://github.com/smarter-sh/smarter/commit/049c444f319ad42abefbf8f845cb0256a635ccd0))

## [0.18.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.18.5...v0.18.6-alpha.1) (2026-10-07)

### Bug Fixes

* **api:** restore legacy cli schema url and exempt schema calls from 404 throttle ([271a922](https://github.com/smarter-sh/smarter/commit/271a922ded5e58b3dbc2a1bcbcf4b19d02b5989d))
* **plugin:** stop tests from deleting the stackademy plugins' data ([7bfd5e7](https://github.com/smarter-sh/smarter/commit/7bfd5e78f4ecd0ea7cafb5c320a17cce36c8a0a8))

### Refactoring

* **react:** host smarter-chat locally, drop the react cdn scheme ([049c444](https://github.com/smarter-sh/smarter/commit/049c444f319ad42abefbf8f845cb0256a635ccd0))

## [0.18.5](https://github.com/smarter-sh/smarter/compare/v0.18.4...v0.18.5) (2026-10-07)

### Bug Fixes

* **llmclient:** stop deploy_builtin_llmclients from undeploying deployed llmclients ([5a1a7dd](https://github.com/smarter-sh/smarter/commit/5a1a7dd80708ce41ae54edf8fab976125943cd6c))

## [0.18.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.18.4...v0.18.5-alpha.1) (2026-10-07)

### Bug Fixes

- **llmclient:** stop deploy_builtin_llmclients from undeploying deployed llmclients ([5a1a7dd](https://github.com/smarter-sh/smarter/commit/5a1a7dd80708ce41ae54edf8fab976125943cd6c))

## [0.18.4](https://github.com/smarter-sh/smarter/compare/v0.18.3...v0.18.4) (2026-10-07)

### Bug Fixes

- **api:** copy the platform domain's A record, never overwrite one ([5ac9747](https://github.com/smarter-sh/smarter/commit/5ac974749bf627465546568b7c46b4301124d128))
- **llmclient:** stop deploy/undeploy race and speed up kubectl calls ([5faaad9](https://github.com/smarter-sh/smarter/commit/5faaad9f4db29adee9ebaf0a82f45ab526a7b9d1))

## [0.18.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.18.4-alpha.1...v0.18.4-alpha.2) (2026-10-07)

### Bug Fixes

- **llmclient:** stop deploy/undeploy race and speed up kubectl calls ([5faaad9](https://github.com/smarter-sh/smarter/commit/5faaad9f4db29adee9ebaf0a82f45ab526a7b9d1))

## [0.18.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.18.3...v0.18.4-alpha.1) (2026-10-06)

### Bug Fixes

- **api:** copy the platform domain's A record, never overwrite one ([5ac9747](https://github.com/smarter-sh/smarter/commit/5ac974749bf627465546568b7c46b4301124d128))

## [0.18.3](https://github.com/smarter-sh/smarter/compare/v0.18.2...v0.18.3) (2026-10-06)

### Bug Fixes

- **api:** copy the platform domain's A record, never overwrite one ([eb6995b](https://github.com/smarter-sh/smarter/commit/eb6995baff0d9e91800edf831d93e8338dbc44e7))

## [0.18.2](https://github.com/smarter-sh/smarter/compare/v0.18.1...v0.18.2) (2026-10-06)

### Bug Fixes

- **infrastructure:** move cloud, kubernetes and email helpers into a service layer ([6a41d4e](https://github.com/smarter-sh/smarter/commit/6a41d4ed44832f74ca610663833b63729de16681))

## [0.18.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.18.1...v0.18.2-alpha.1) (2026-10-06)

### Bug Fixes

- **infrastructure:** move cloud, kubernetes and email helpers into a service layer ([6a41d4e](https://github.com/smarter-sh/smarter/commit/6a41d4ed44832f74ca610663833b63729de16681))

## [0.18.1](https://github.com/smarter-sh/smarter/compare/v0.18.0...v0.18.1) (2026-10-06)

### Bug Fixes

- fix five bugs found while raising test coverage by ~1,000 lines ([c97f2a4](https://github.com/smarter-sh/smarter/commit/c97f2a475017fde4d289c856b3ed6576b1d67428))
- **settings:** stop logging SECRET*KEY and DJANGO*\* override values ([1bae42a](https://github.com/smarter-sh/smarter/commit/1bae42a88f65e37d2e63029ba7b0443d57bfe254)), closes [smarter-sh/smarter#760](https://github.com/smarter-sh/smarter/issues/760)

### Refactoring

- remove shadowing secret commands, repair docstrings and docs ([063da2f](https://github.com/smarter-sh/smarter/commit/063da2f8124ec62a34e97d47393c35e6cf9fc655))

## [0.18.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.18.1-alpha.1...v0.18.1-alpha.2) (2026-10-06)

### Bug Fixes

- fix five bugs found while raising test coverage by ~1,000 lines ([c97f2a4](https://github.com/smarter-sh/smarter/commit/c97f2a475017fde4d289c856b3ed6576b1d67428))

## [0.18.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.18.0...v0.18.1-alpha.1) (2026-10-06)

### Bug Fixes

- **settings:** stop logging SECRET*KEY and DJANGO*\* override values ([1bae42a](https://github.com/smarter-sh/smarter/commit/1bae42a88f65e37d2e63029ba7b0443d57bfe254)), closes [smarter-sh/smarter#760](https://github.com/smarter-sh/smarter/issues/760)

### Refactoring

- remove shadowing secret commands, repair docstrings and docs ([063da2f](https://github.com/smarter-sh/smarter/commit/063da2f8124ec62a34e97d47393c35e6cf9fc655))

## [0.18.0](https://github.com/smarter-sh/smarter/compare/v0.17.3...v0.18.0) (2026-10-05)

### Features

- **llmclient:** make Custom Domain a SAM resource, with verification and a web console list ([b5b13d0](https://github.com/smarter-sh/smarter/commit/b5b13d0a649cc39179ab2dc8c405400edba63238))

### Bug Fixes

- **passthrough:** make the prompt passthrough work across providers, and test every template against every provider ([68ba9a5](https://github.com/smarter-sh/smarter/commit/68ba9a5fa62b29837bd2ff5476f5aeef2c7e0ad5))

## [0.18.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.17.4-alpha.1...v0.18.0-alpha.1) (2026-10-05)

### Features

- **llmclient:** make Custom Domain a SAM resource, with verification and a web console list ([b5b13d0](https://github.com/smarter-sh/smarter/commit/b5b13d0a649cc39179ab2dc8c405400edba63238))
