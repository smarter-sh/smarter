# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.44.13-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.44.13-alpha.1...v0.44.13-alpha.2) (2026-11-11)

### Bug Fixes

* **dashboard:** don't log a warning for an anonymous user's admin module permission ([fb035b4](https://github.com/smarter-sh/smarter/commit/fb035b47cc8c613c11c42ead3be2c4e24f440f70)), closes [#979](https://github.com/smarter-sh/smarter/issues/979)

## [0.44.13-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.12...v0.44.13-alpha.1) (2026-11-11)

### Bug Fixes

* **skills:** download the smarter-api deployment's inventory and logs in download-logs.sh ([014d3cf](https://github.com/smarter-sh/smarter/commit/014d3cf707afa559bb3b472963dbdf04caa6f8b2)), closes [#982](https://github.com/smarter-sh/smarter/issues/982)

## [0.44.12](https://github.com/smarter-sh/smarter/compare/v0.44.11...v0.44.12) (2026-11-10)

### Bug Fixes

* **helm:** accept null AWS keys when the pods have an IAM role ([b33eb84](https://github.com/smarter-sh/smarter/commit/b33eb84f1e915ef3ecdd4d6349a2155460d2f6ae))

## [0.44.12-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.11...v0.44.12-alpha.1) (2026-11-10)

### Bug Fixes

* **helm:** accept null AWS keys when the pods have an IAM role ([b33eb84](https://github.com/smarter-sh/smarter/commit/b33eb84f1e915ef3ecdd4d6349a2155460d2f6ae))

## [0.44.11](https://github.com/smarter-sh/smarter/compare/v0.44.10...v0.44.11) (2026-11-10)

### Bug Fixes

* **infrastructure:** run pods as a ServiceAccount with an IAM role ([56bec59](https://github.com/smarter-sh/smarter/commit/56bec596d7bdfff17052b4cfc04a1f00cd820b37))
* **llmclient:** use one DNS zone for local deploys and deletes ([37d718c](https://github.com/smarter-sh/smarter/commit/37d718c423a846f845cdeab0b9ea11cc7ddb5382))

## [0.44.11-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.10...v0.44.11-alpha.1) (2026-11-10)

### Bug Fixes

* **infrastructure:** run pods as a ServiceAccount with an IAM role ([56bec59](https://github.com/smarter-sh/smarter/commit/56bec596d7bdfff17052b4cfc04a1f00cd820b37))
* **llmclient:** use one DNS zone for local deploys and deletes ([37d718c](https://github.com/smarter-sh/smarter/commit/37d718c423a846f845cdeab0b9ea11cc7ddb5382))

## [0.44.10-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.44.10-alpha.1...v0.44.10-alpha.2) (2026-11-10)

### Bug Fixes

- **account:** give each of a user's API keys a different name ([a2ee061](https://github.com/smarter-sh/smarter/commit/a2ee0614f572db16022ff3f1ac47b2bb9aded36e)), closes [#971](https://github.com/smarter-sh/smarter/issues/971)
- **api:** log a rejected cli request at WARNING, without instructions ([302ebe3](https://github.com/smarter-sh/smarter/commit/302ebe3f7065dbfc8d92cc3cda8942ba60ddaddf)), closes [#972](https://github.com/smarter-sh/smarter/issues/972)
- **infrastructure:** don't log the sender of a failed email ([35cb310](https://github.com/smarter-sh/smarter/commit/35cb3109834d03e777248895eb8c48760ad43fc4)), closes [#961](https://github.com/smarter-sh/smarter/issues/961) [#973](https://github.com/smarter-sh/smarter/issues/973)
- **manifest:** log a broker that is not ready at DEBUG, not WARNING ([e9cc54b](https://github.com/smarter-sh/smarter/commit/e9cc54b648aae84ed92d54cd92bd1fa41ceaabb4)), closes [#952](https://github.com/smarter-sh/smarter/issues/952) [#974](https://github.com/smarter-sh/smarter/issues/974)
- **passthrough:** never log a passthrough request's chat content ([f66507a](https://github.com/smarter-sh/smarter/commit/f66507a28e3a214c4c6c59ad93610924c0aabe2e)), closes [#933](https://github.com/smarter-sh/smarter/issues/933) [#937](https://github.com/smarter-sh/smarter/issues/937) [#970](https://github.com/smarter-sh/smarter/issues/970)

## [0.44.10-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.9...v0.44.10-alpha.1) (2026-11-10)

### Bug Fixes

- **prompt:** log a summary of a failed prompt's iteration, not its chat content ([7c00560](https://github.com/smarter-sh/smarter/commit/7c0056008064804bfc4a2b52b7e5d2121e211963)), closes [#970](https://github.com/smarter-sh/smarter/issues/970)

## [0.44.9](https://github.com/smarter-sh/smarter/compare/v0.44.8...v0.44.9) (2026-11-10)

### Bug Fixes

- **helm:** let the api rollout stop an old pod when no node has room ([f732111](https://github.com/smarter-sh/smarter/commit/f732111c9c4370b0123e0fd4ffd13053823c5bb6))

## [0.44.9-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.8...v0.44.9-alpha.1) (2026-11-10)

### Bug Fixes

- **helm:** let the api rollout stop an old pod when no node has room ([f732111](https://github.com/smarter-sh/smarter/commit/f732111c9c4370b0123e0fd4ffd13053823c5bb6))

## [0.44.9-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.8...v0.44.9-alpha.1) (2026-11-10)

### Bug Fixes

- **helm:** let the api rollout stop an old pod when no node has room ([1a0edd3](https://github.com/smarter-sh/smarter/commit/1a0edd37a5d0a2c44e9bcdb7ba889e24dc163a9f))

## [0.44.8](https://github.com/smarter-sh/smarter/compare/v0.44.7...v0.44.8) (2026-11-10)

### Bug Fixes

- **security:** stop logging api keys, passwords and secret values ([d1427e1](https://github.com/smarter-sh/smarter/commit/d1427e10f3ea60d064cd1c35b349166435129d70))

## [0.44.8-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.7...v0.44.8-alpha.1) (2026-11-10)

### Bug Fixes

- **security:** stop logging api keys, passwords and secret values ([d1427e1](https://github.com/smarter-sh/smarter/commit/d1427e10f3ea60d064cd1c35b349166435129d70))

## [0.44.7](https://github.com/smarter-sh/smarter/compare/v0.44.6...v0.44.7) (2026-11-10)

### Bug Fixes

- resolve every mypy error and add mypy to the pre-commit hooks ([4afc95a](https://github.com/smarter-sh/smarter/commit/4afc95a244f642a22532278eb2a0965670500fce))

## [0.44.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.6...v0.44.7-alpha.1) (2026-11-10)

### Bug Fixes

- resolve every mypy error and add mypy to the pre-commit hooks ([4afc95a](https://github.com/smarter-sh/smarter/commit/4afc95a244f642a22532278eb2a0965670500fce))

## [0.44.6](https://github.com/smarter-sh/smarter/compare/v0.44.5...v0.44.6) (2026-11-09)

### Bug Fixes

- **celery:** shorten RedBeat's lock so Beat recovers soon after a crash ([aa86a25](https://github.com/smarter-sh/smarter/commit/aa86a25204f2670b45cdb92b1fa1c6a3d76b9b2d)), closes [#964](https://github.com/smarter-sh/smarter/issues/964) [#945](https://github.com/smarter-sh/smarter/issues/945)
- **django:** answer 405, not 500, to a GET of a view without a template ([5b2c907](https://github.com/smarter-sh/smarter/commit/5b2c90787fbd37a968acafb3d4926b2ada7236d2)), closes [#963](https://github.com/smarter-sh/smarter/issues/963)
- **secret:** return the broker's name, and log a missing one at debug ([0a4d4ab](https://github.com/smarter-sh/smarter/commit/0a4d4ab4b43475a7d97668f699eaceec54c9e2a5)), closes [#965](https://github.com/smarter-sh/smarter/issues/965)

## [0.44.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.5...v0.44.6-alpha.1) (2026-11-09)

### Bug Fixes

- **celery:** shorten RedBeat's lock so Beat recovers soon after a crash ([aa86a25](https://github.com/smarter-sh/smarter/commit/aa86a25204f2670b45cdb92b1fa1c6a3d76b9b2d)), closes [#964](https://github.com/smarter-sh/smarter/issues/964) [#945](https://github.com/smarter-sh/smarter/issues/945)
- **django:** answer 405, not 500, to a GET of a view without a template ([5b2c907](https://github.com/smarter-sh/smarter/commit/5b2c90787fbd37a968acafb3d4926b2ada7236d2)), closes [#963](https://github.com/smarter-sh/smarter/issues/963)
- **secret:** return the broker's name, and log a missing one at debug ([0a4d4ab](https://github.com/smarter-sh/smarter/commit/0a4d4ab4b43475a7d97668f699eaceec54c9e2a5)), closes [#965](https://github.com/smarter-sh/smarter/issues/965)

## [0.44.5](https://github.com/smarter-sh/smarter/compare/v0.44.4...v0.44.5) (2026-11-09)

### Bug Fixes

- bump smarter-console to v1.1.6 ([0409437](https://github.com/smarter-sh/smarter/commit/0409437a97d4328b4f6d045c605ea2716a0dbdfd))

## [0.44.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.4...v0.44.5-alpha.1) (2026-11-09)

### Bug Fixes

- bump smarter-console to v1.1.6 ([0409437](https://github.com/smarter-sh/smarter/commit/0409437a97d4328b4f6d045c605ea2716a0dbdfd))

## [0.44.4](https://github.com/smarter-sh/smarter/compare/v0.44.3...v0.44.4) (2026-11-09)

### Bug Fixes

- force a new release ([35173ce](https://github.com/smarter-sh/smarter/commit/35173ce0b20e794b9063d31686c8e2a43a7b3a44))

## [0.44.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.3...v0.44.4-alpha.1) (2026-11-09)

### Bug Fixes

- force a new release ([35173ce](https://github.com/smarter-sh/smarter/commit/35173ce0b20e794b9063d31686c8e2a43a7b3a44))

## [0.44.3](https://github.com/smarter-sh/smarter/compare/v0.44.2...v0.44.3) (2026-11-08)

### Bug Fixes

- **llmclient:** honor what each openai model accepts, and validate it ([dc4da40](https://github.com/smarter-sh/smarter/commit/dc4da40f3660a4bcf3dad19d1b7181cffdd58eb7))

## [0.44.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.2...v0.44.3-alpha.1) (2026-11-08)

### Bug Fixes

- **llmclient:** honor what each openai model accepts, and validate it ([dc4da40](https://github.com/smarter-sh/smarter/commit/dc4da40f3660a4bcf3dad19d1b7181cffdd58eb7))

## [0.44.2](https://github.com/smarter-sh/smarter/compare/v0.44.1...v0.44.2) (2026-11-08)

### Bug Fixes

- **account:** log the static files upload in initialize_platform ([b5b26eb](https://github.com/smarter-sh/smarter/commit/b5b26eb60c2ae25cd9acb1a289f954cd7cc4d6b4))
- **prompt:** add a provider request api for the chat's sandbox mode ([994f00e](https://github.com/smarter-sh/smarter/commit/994f00eca2f7c05d51697a00aad196449f4af339))

## [0.44.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.44.2-alpha.1...v0.44.2-alpha.2) (2026-11-08)

### Bug Fixes

- **account:** log the static files upload in initialize_platform ([b5b26eb](https://github.com/smarter-sh/smarter/commit/b5b26eb60c2ae25cd9acb1a289f954cd7cc4d6b4))

## [0.44.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.1...v0.44.2-alpha.1) (2026-11-08)

### Bug Fixes

- **prompt:** add a provider request api for the chat's sandbox mode ([994f00e](https://github.com/smarter-sh/smarter/commit/994f00eca2f7c05d51697a00aad196449f4af339))

## [0.44.1](https://github.com/smarter-sh/smarter/compare/v0.44.0...v0.44.1) (2026-11-08)

### Bug Fixes

- **account:** give every email one mail-safe layout and working images ([2f7dd1a](https://github.com/smarter-sh/smarter/commit/2f7dd1a56dc81f834c579ec45d05f1c2d8899b01)), closes [#954](https://github.com/smarter-sh/smarter/issues/954)

## [0.44.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.0...v0.44.1-alpha.1) (2026-11-08)

### Bug Fixes

- **account:** give every email one mail-safe layout and working images ([2f7dd1a](https://github.com/smarter-sh/smarter/commit/2f7dd1a56dc81f834c579ec45d05f1c2d8899b01)), closes [#954](https://github.com/smarter-sh/smarter/issues/954)

## [0.44.0](https://github.com/smarter-sh/smarter/compare/v0.43.2...v0.44.0) (2026-11-08)

### Features

- **account:** email users a zip of every manifest that they own ([bb70933](https://github.com/smarter-sh/smarter/commit/bb70933eedf7cab21ce81edf54c5635f09c57002))

### Bug Fixes

- bump smarter-console to v1.1.0 ([74c4c86](https://github.com/smarter-sh/smarter/commit/74c4c86b71e50e4b1d1e912d8e95f6fb64a79fe3))
- **manifest:** log a broker without a name at debug, not as a warning ([700eac6](https://github.com/smarter-sh/smarter/commit/700eac686c6ab5e9602cc6769dfa70a7e483b4de)), closes [#952](https://github.com/smarter-sh/smarter/issues/952)
- **waffle:** log a database outage in switch_is_active() as one warning line ([ff7d343](https://github.com/smarter-sh/smarter/commit/ff7d343d55287c1fb9d8f30403c6261ee34f5103)), closes [#951](https://github.com/smarter-sh/smarter/issues/951)

## [0.44.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.44.0-alpha.2...v0.44.0-alpha.3) (2026-11-08)

### Bug Fixes

- bump smarter-console to v1.1.0 ([74c4c86](https://github.com/smarter-sh/smarter/commit/74c4c86b71e50e4b1d1e912d8e95f6fb64a79fe3))

## [0.44.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.44.0-alpha.1...v0.44.0-alpha.2) (2026-11-08)

### Bug Fixes

- **manifest:** log a broker without a name at debug, not as a warning ([700eac6](https://github.com/smarter-sh/smarter/commit/700eac686c6ab5e9602cc6769dfa70a7e483b4de)), closes [#952](https://github.com/smarter-sh/smarter/issues/952)

## [0.44.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.43.3-alpha.1...v0.44.0-alpha.1) (2026-11-08)

### Features

- **account:** email users a zip of every manifest that they own ([bb70933](https://github.com/smarter-sh/smarter/commit/bb70933eedf7cab21ce81edf54c5635f09c57002))
