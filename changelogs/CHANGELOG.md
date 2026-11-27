# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.48.13-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.12...v0.48.13-alpha.1) (2026-11-27)

### Bug Fixes

* **llmtool:** run extensions' tool calls in a worker of their own ([0cb303a](https://github.com/smarter-sh/smarter/commit/0cb303a9be289e22d1126e8daa68141609c60328)), closes [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.12](https://github.com/smarter-sh/smarter/compare/v0.48.11...v0.48.12) (2026-11-27)

### Bug Fixes

* **infrastructure:** sum up the tool worker's startup checks ([db2b97a](https://github.com/smarter-sh/smarter/commit/db2b97ae34d34200a44122749c3ed29b8c574688))

## [0.48.12-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.11...v0.48.12-alpha.1) (2026-11-27)

### Bug Fixes

* **infrastructure:** sum up the tool worker's startup checks ([db2b97a](https://github.com/smarter-sh/smarter/commit/db2b97ae34d34200a44122749c3ed29b8c574688))

## [0.48.11](https://github.com/smarter-sh/smarter/compare/v0.48.10...v0.48.11) (2026-11-27)

### Bug Fixes

* **helm:** check the tool worker's liveness without pinging it ([89487b4](https://github.com/smarter-sh/smarter/commit/89487b49c6205b0ef50dc267eb3938cad63824e7))

## [0.48.11-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.10...v0.48.11-alpha.1) (2026-11-27)

### Bug Fixes

* **helm:** check the tool worker's liveness without pinging it ([89487b4](https://github.com/smarter-sh/smarter/commit/89487b49c6205b0ef50dc267eb3938cad63824e7))

## [0.48.10](https://github.com/smarter-sh/smarter/compare/v0.48.9...v0.48.10) (2026-11-27)

### Bug Fixes

* **helm:** define redis's tools user at start, not with auth.acl ([260bd6e](https://github.com/smarter-sh/smarter/commit/260bd6ef52025d3e178aad167fbab0d93f6ada1c))

## [0.48.10-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.9...v0.48.10-alpha.1) (2026-11-27)

### Bug Fixes

* **helm:** define redis's tools user at start, not with auth.acl ([260bd6e](https://github.com/smarter-sh/smarter/commit/260bd6ef52025d3e178aad167fbab0d93f6ada1c))

## [0.48.9](https://github.com/smarter-sh/smarter/compare/v0.48.8...v0.48.9) (2026-11-27)

### Bug Fixes

* **docker:** give build-time manage.py a throwaway redis password ([0274b0a](https://github.com/smarter-sh/smarter/commit/0274b0a3308ce73daa70874cfb4d0a3ddcfc7e0e)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)
* **llmtool:** give the tool worker a redis acl user of its own ([5e20664](https://github.com/smarter-sh/smarter/commit/5e206644b075af8993298d450b078f52bb845026)), closes [#1065](https://github.com/smarter-sh/smarter/issues/1065) [#1073](https://github.com/smarter-sh/smarter/issues/1073) [#1077](https://github.com/smarter-sh/smarter/issues/1077)
* **settings:** generate redis's password per environment, never public ([d1a7d32](https://github.com/smarter-sh/smarter/commit/d1a7d32524da7335ad78a55255d3c28080998603)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)

## [0.48.9-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.9-alpha.1...v0.48.9-alpha.2) (2026-11-27)

### Bug Fixes

* **docker:** give build-time manage.py a throwaway redis password ([0274b0a](https://github.com/smarter-sh/smarter/commit/0274b0a3308ce73daa70874cfb4d0a3ddcfc7e0e)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)
* **llmtool:** give the tool worker a redis acl user of its own ([5e20664](https://github.com/smarter-sh/smarter/commit/5e206644b075af8993298d450b078f52bb845026)), closes [#1065](https://github.com/smarter-sh/smarter/issues/1065) [#1073](https://github.com/smarter-sh/smarter/issues/1073) [#1077](https://github.com/smarter-sh/smarter/issues/1077)

## [0.48.9-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.8...v0.48.9-alpha.1) (2026-11-27)

### Bug Fixes

* **settings:** generate redis's password per environment, never public ([d1a7d32](https://github.com/smarter-sh/smarter/commit/d1a7d32524da7335ad78a55255d3c28080998603)), closes [#1073](https://github.com/smarter-sh/smarter/issues/1073)

## [0.48.8](https://github.com/smarter-sh/smarter/compare/v0.48.7...v0.48.8) (2026-11-27)

### Bug Fixes

* **api:** log api requests' users by id, not username ([395248b](https://github.com/smarter-sh/smarter/commit/395248bb96c431fc70729e6ced7c339e03acd097)), closes [#1067](https://github.com/smarter-sh/smarter/issues/1067)
* **llmclient:** roll back a new llmclient when its apply fails ([ac903e5](https://github.com/smarter-sh/smarter/commit/ac903e56df9a30b17936bde9b61aff5a2f71f9fe))
* **settings:** confirm smtp is disabled in the tool worker ([adbbf8c](https://github.com/smarter-sh/smarter/commit/adbbf8c7d1cd809d18ca05b70ab8e3400c61dab3))

## [0.48.8-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.8-alpha.1...v0.48.8-alpha.2) (2026-11-27)

### Bug Fixes

* **llmclient:** roll back a new llmclient when its apply fails ([ac903e5](https://github.com/smarter-sh/smarter/commit/ac903e56df9a30b17936bde9b61aff5a2f71f9fe))
* **settings:** confirm smtp is disabled in the tool worker ([adbbf8c](https://github.com/smarter-sh/smarter/commit/adbbf8c7d1cd809d18ca05b70ab8e3400c61dab3))

## [0.48.8-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.7...v0.48.8-alpha.1) (2026-11-27)

### Bug Fixes

* **api:** log api requests' users by id, not username ([395248b](https://github.com/smarter-sh/smarter/commit/395248bb96c431fc70729e6ced7c339e03acd097)), closes [#1067](https://github.com/smarter-sh/smarter/issues/1067)

## [0.48.7](https://github.com/smarter-sh/smarter/compare/v0.48.6...v0.48.7) (2026-11-26)

### Bug Fixes

* **infrastructure:** add startup checks, confirm tool worker isolation ([7bd2b67](https://github.com/smarter-sh/smarter/commit/7bd2b67c47a7b7e0b601c90ec143560e0a9e423d))

## [0.48.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.6...v0.48.7-alpha.1) (2026-11-26)

### Bug Fixes

* **infrastructure:** add startup checks, confirm tool worker isolation ([7bd2b67](https://github.com/smarter-sh/smarter/commit/7bd2b67c47a7b7e0b601c90ec143560e0a9e423d))

## [0.48.6](https://github.com/smarter-sh/smarter/compare/v0.48.5...v0.48.6) (2026-11-26)

### Bug Fixes

* **celery:** register only run_tool_call in the tool worker ([6c146c0](https://github.com/smarter-sh/smarter/commit/6c146c070008c652416c2d3606f09efc4cf098a3))
* **llmclient:** log the url and LLMClient that the middleware verified ([3c51d0d](https://github.com/smarter-sh/smarter/commit/3c51d0d3bb83be21f89f933e02cbf28a1c993305))

## [0.48.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.5...v0.48.6-alpha.1) (2026-11-26)

### Bug Fixes

* **celery:** register only run_tool_call in the tool worker ([6c146c0](https://github.com/smarter-sh/smarter/commit/6c146c070008c652416c2d3606f09efc4cf098a3))
* **llmclient:** log the url and LLMClient that the middleware verified ([3c51d0d](https://github.com/smarter-sh/smarter/commit/3c51d0d3bb83be21f89f933e02cbf28a1c993305))

## [0.48.5](https://github.com/smarter-sh/smarter/compare/v0.48.4...v0.48.5) (2026-11-26)

### Bug Fixes

* **llmtool:** log one labeled line per tool call in the tool worker ([eea7350](https://github.com/smarter-sh/smarter/commit/eea7350a2984e2629529c07ab5d7fca281088095))
* **logging:** log prompts by id and simplify verbose request messages ([c09e0d6](https://github.com/smarter-sh/smarter/commit/c09e0d63c27037b6a4677f029f9840c824278803))

### Refactoring

* import json from smarter.lib everywhere in the package ([15c4e55](https://github.com/smarter-sh/smarter/commit/15c4e559f76def70a6ec196ddba7e821bc00881d))

## [0.48.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.4...v0.48.5-alpha.1) (2026-11-26)

### Bug Fixes

* **llmtool:** log one labeled line per tool call in the tool worker ([eea7350](https://github.com/smarter-sh/smarter/commit/eea7350a2984e2629529c07ab5d7fca281088095))
* **logging:** log prompts by id and simplify verbose request messages ([c09e0d6](https://github.com/smarter-sh/smarter/commit/c09e0d63c27037b6a4677f029f9840c824278803))

### Refactoring

* import json from smarter.lib everywhere in the package ([15c4e55](https://github.com/smarter-sh/smarter/commit/15c4e559f76def70a6ec196ddba7e821bc00881d))

## [0.48.4](https://github.com/smarter-sh/smarter/compare/v0.48.3...v0.48.4) (2026-11-26)

### Bug Fixes

* **connection:** describe shows Secrets' names, never their values ([28767e9](https://github.com/smarter-sh/smarter/commit/28767e9771d44818fa800ca4fd0599ba7fe74efb))
* **connection:** make the SqlConnection SSH tunnel work, via the runner ([d320401](https://github.com/smarter-sh/smarter/commit/d32040170b3cb547c6e0bf2ec763fcebc52f69c8))
* **connection:** refuse api connection urls that aren't public (SSRF) ([4ce9e59](https://github.com/smarter-sh/smarter/commit/4ce9e597026a61e41aee04773de88a7c0dc63d16))
* **helm:** deploy the tool worker, off by default ([48a485c](https://github.com/smarter-sh/smarter/commit/48a485c7c81eafead26b5885d6e65dbbad3a8b50))
* **llmtool:** run tool calls in a worker without credentials ([8f7285c](https://github.com/smarter-sh/smarter/commit/8f7285c386492c8da8122a4e20620e17e2b4e05a))

### Refactoring

* **connection:** run ApiPlugin requests through the tool runner ([f5842ab](https://github.com/smarter-sh/smarter/commit/f5842ab4cd233f410a4d1c602b0c0c5f121f45c3))
* **llmtool:** run Extension tool calls through the tool runner ([fa04d8f](https://github.com/smarter-sh/smarter/commit/fa04d8f1fbaa622cca3d11ea27083d749094bb96))
* **llmtool:** run web and image search requests through the runner ([d53ebcd](https://github.com/smarter-sh/smarter/commit/d53ebcde3037858fefea1220e440ccb235de8ecc))
* **llmtool:** run web search page fetches through the tool runner ([a88d0f2](https://github.com/smarter-sh/smarter/commit/a88d0f28176c849c780d013655ce47875b1d961e))
* **mcpclient:** run MCP tool calls through the new tool runner ([3114186](https://github.com/smarter-sh/smarter/commit/31141865e03a21678e2217213511e78df11293b6))

## [0.48.4-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.48.4-alpha.3...v0.48.4-alpha.4) (2026-11-26)

### Bug Fixes

* **helm:** deploy the tool worker, off by default ([48a485c](https://github.com/smarter-sh/smarter/commit/48a485c7c81eafead26b5885d6e65dbbad3a8b50))
* **llmtool:** run tool calls in a worker without credentials ([8f7285c](https://github.com/smarter-sh/smarter/commit/8f7285c386492c8da8122a4e20620e17e2b4e05a))

## [0.48.4-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.48.4-alpha.2...v0.48.4-alpha.3) (2026-11-26)

### Bug Fixes

* **connection:** describe shows Secrets' names, never their values ([28767e9](https://github.com/smarter-sh/smarter/commit/28767e9771d44818fa800ca4fd0599ba7fe74efb))

### Refactoring

* **llmtool:** run Extension tool calls through the tool runner ([fa04d8f](https://github.com/smarter-sh/smarter/commit/fa04d8f1fbaa622cca3d11ea27083d749094bb96))

## [0.48.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.48.4-alpha.1...v0.48.4-alpha.2) (2026-11-26)

### Bug Fixes

* **connection:** make the SqlConnection SSH tunnel work, via the runner ([d320401](https://github.com/smarter-sh/smarter/commit/d32040170b3cb547c6e0bf2ec763fcebc52f69c8))

### Refactoring

* **connection:** run ApiPlugin requests through the tool runner ([f5842ab](https://github.com/smarter-sh/smarter/commit/f5842ab4cd233f410a4d1c602b0c0c5f121f45c3))
* **llmtool:** run web and image search requests through the runner ([d53ebcd](https://github.com/smarter-sh/smarter/commit/d53ebcde3037858fefea1220e440ccb235de8ecc))
* **llmtool:** run web search page fetches through the tool runner ([a88d0f2](https://github.com/smarter-sh/smarter/commit/a88d0f28176c849c780d013655ce47875b1d961e))
* **mcpclient:** run MCP tool calls through the new tool runner ([3114186](https://github.com/smarter-sh/smarter/commit/31141865e03a21678e2217213511e78df11293b6))

## [0.48.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.48.3...v0.48.4-alpha.1) (2026-11-26)

### Bug Fixes

* **connection:** refuse api connection urls that aren't public (SSRF) ([4ce9e59](https://github.com/smarter-sh/smarter/commit/4ce9e597026a61e41aee04773de88a7c0dc63d16))

## [0.48.3](https://github.com/smarter-sh/smarter/compare/v0.48.2...v0.48.3) (2026-11-25)

### Bug Fixes

* **account:** log users by id, not username, on sign-in and User saves ([2154890](https://github.com/smarter-sh/smarter/commit/2154890d6125da358f51575f4c0b9cd4f64068fa)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1055](https://github.com/smarter-sh/smarter/issues/1055) [#1055](https://github.com/smarter-sh/smarter/issues/1055)
* **helm:** default the image to mcdaniel0073/smarter on docker hub ([3b1d771](https://github.com/smarter-sh/smarter/commit/3b1d7711526999b5e76cc78dcff0a4cc7c8cce80))

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
