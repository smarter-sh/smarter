# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.46.20-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.19...v0.46.20-alpha.1) (2026-11-23)

### Bug Fixes

* **guardrail:** stop the llm_judge system message from judging safety ([bf147a9](https://github.com/smarter-sh/smarter/commit/bf147a9fc7aebae31280a93077934839e287c6f0))

## [0.46.19](https://github.com/smarter-sh/smarter/compare/v0.46.18...v0.46.19) (2026-11-23)

### Bug Fixes

* **llmclient:** refresh cached answers when apply changes what it uses ([0a31d9e](https://github.com/smarter-sh/smarter/commit/0a31d9e5a517ba1f1d5926a3b4e1a55bbeefbe1b))
* **llmtool:** stop failed applies leaving plugins that never load ([93552fa](https://github.com/smarter-sh/smarter/commit/93552fae3158465db477b12f82e208294975c1ec))

## [0.46.19-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.18...v0.46.19-alpha.1) (2026-11-23)

### Bug Fixes

* **llmclient:** refresh cached answers when apply changes what it uses ([0a31d9e](https://github.com/smarter-sh/smarter/commit/0a31d9e5a517ba1f1d5926a3b4e1a55bbeefbe1b))
* **llmtool:** stop failed applies leaving plugins that never load ([93552fa](https://github.com/smarter-sh/smarter/commit/93552fae3158465db477b12f82e208294975c1ec))

## [0.46.18](https://github.com/smarter-sh/smarter/compare/v0.46.17...v0.46.18) (2026-11-23)

### Bug Fixes

* **logging:** name settings and url logs after their caller ([481147a](https://github.com/smarter-sh/smarter/commit/481147a196e243c8de7c10e5ed955633023db0e1))
* **settings:** rename user settings to overrides ([21412ae](https://github.com/smarter-sh/smarter/commit/21412aeebb74bddebf5f5e055ebb5a321277f738))

## [0.46.18-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.18-alpha.1...v0.46.18-alpha.2) (2026-11-23)

### Bug Fixes

* **logging:** name settings and url logs after their caller ([481147a](https://github.com/smarter-sh/smarter/commit/481147a196e243c8de7c10e5ed955633023db0e1))

## [0.46.18-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.17...v0.46.18-alpha.1) (2026-11-22)

### Bug Fixes

* **settings:** rename user settings to overrides ([21412ae](https://github.com/smarter-sh/smarter/commit/21412aeebb74bddebf5f5e055ebb5a321277f738))

## [0.46.17](https://github.com/smarter-sh/smarter/compare/v0.46.16...v0.46.17) (2026-11-22)

### Bug Fixes

* **helm:** migrate with the new release's settings, not the old ([defd1cd](https://github.com/smarter-sh/smarter/commit/defd1cdb2f21dac1a2c8d6e069d19789552e9cef))

## [0.46.17-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.16...v0.46.17-alpha.1) (2026-11-22)

### Bug Fixes

* **helm:** migrate with the new release's settings, not the old ([defd1cd](https://github.com/smarter-sh/smarter/commit/defd1cdb2f21dac1a2c8d6e069d19789552e9cef))

## [0.46.16](https://github.com/smarter-sh/smarter/compare/v0.46.15...v0.46.16) (2026-11-22)

### Bug Fixes

* **deploy:** write the chart's boolean settings as JSON booleans ([3d73af9](https://github.com/smarter-sh/smarter/commit/3d73af94d0aa7b715c375247fe2d56f11eaf98b9))
* **helm:** install the chart with a values file, no deploy workflow ([c7622a2](https://github.com/smarter-sh/smarter/commit/c7622a2b7554af523d097c22c3b7ade90a29c9ed))

## [0.46.16-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.16-alpha.1...v0.46.16-alpha.2) (2026-11-22)

### Bug Fixes

* **deploy:** write the chart's boolean settings as JSON booleans ([3d73af9](https://github.com/smarter-sh/smarter/commit/3d73af94d0aa7b715c375247fe2d56f11eaf98b9))

## [0.46.16-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.15...v0.46.16-alpha.1) (2026-11-22)

### Bug Fixes

* **helm:** install the chart with a values file, no deploy workflow ([c7622a2](https://github.com/smarter-sh/smarter/commit/c7622a2b7554af523d097c22c3b7ade90a29c9ed))

## [0.46.15](https://github.com/smarter-sh/smarter/compare/v0.46.14...v0.46.15) (2026-11-22)

### Bug Fixes

* **account:** stop creating the staff_user example user ([4eebe02](https://github.com/smarter-sh/smarter/commit/4eebe02368a93b844cc94e48c5706dd62992fc46))
* **helm:** hold a fresh install's pods for its database, run init once ([8df9a41](https://github.com/smarter-sh/smarter/commit/8df9a41af3f6a1aa855ccf30b638b1d008c6dac5))
* **settings:** set each logged environment variable off with a dash ([63e1e8c](https://github.com/smarter-sh/smarter/commit/63e1e8c74a0ef5796b7854771af7030217802122))

## [0.46.15-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.14...v0.46.15-alpha.1) (2026-11-22)

### Bug Fixes

* **account:** stop creating the staff_user example user ([4eebe02](https://github.com/smarter-sh/smarter/commit/4eebe02368a93b844cc94e48c5706dd62992fc46))
* **helm:** hold a fresh install's pods for its database, run init once ([8df9a41](https://github.com/smarter-sh/smarter/commit/8df9a41af3f6a1aa855ccf30b638b1d008c6dac5))
* **settings:** set each logged environment variable off with a dash ([63e1e8c](https://github.com/smarter-sh/smarter/commit/63e1e8c74a0ef5796b7854771af7030217802122))

## [0.46.14](https://github.com/smarter-sh/smarter/compare/v0.46.13...v0.46.14) (2026-11-22)

### Bug Fixes

* **logging:** log only through getSmarterLogger; unquote env values ([82bd2bd](https://github.com/smarter-sh/smarter/commit/82bd2bd66406fc616733d1d90612ebbdd51f707f))
* **manifest:** word the SAM apps' readiness log in the singular ([3accbff](https://github.com/smarter-sh/smarter/commit/3accbff7a852590b55f5e2bc80fb4455660dd650))
* **settings:** group env vars by platform, subsystem and app ([1a4ed07](https://github.com/smarter-sh/smarter/commit/1a4ed078f40006ac03fff66d00e666a58957ced9))
* **templates:** link the web app manifest only on hosts whose urlconf serves it ([e452bf2](https://github.com/smarter-sh/smarter/commit/e452bf275a49ec7cfffa0cfcd6257f0f6e20c3a3)), closes [#1032](https://github.com/smarter-sh/smarter/issues/1032)

### Refactoring

* **settings:** declare defaults on fields, read env with Pydantic ([658f150](https://github.com/smarter-sh/smarter/commit/658f150bc0149e695463eecd46b6155abb714ef2))

## [0.46.14-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.46.14-alpha.3...v0.46.14-alpha.4) (2026-11-22)

### Bug Fixes

* **templates:** link the web app manifest only on hosts whose urlconf serves it ([e452bf2](https://github.com/smarter-sh/smarter/commit/e452bf275a49ec7cfffa0cfcd6257f0f6e20c3a3)), closes [#1032](https://github.com/smarter-sh/smarter/issues/1032)

## [0.46.14-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.46.14-alpha.2...v0.46.14-alpha.3) (2026-11-22)

### Bug Fixes

* **logging:** log only through getSmarterLogger; unquote env values ([82bd2bd](https://github.com/smarter-sh/smarter/commit/82bd2bd66406fc616733d1d90612ebbdd51f707f))

## [0.46.14-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.14-alpha.1...v0.46.14-alpha.2) (2026-11-22)

### Bug Fixes

* **manifest:** word the SAM apps' readiness log in the singular ([3accbff](https://github.com/smarter-sh/smarter/commit/3accbff7a852590b55f5e2bc80fb4455660dd650))

### Refactoring

* **settings:** declare defaults on fields, read env with Pydantic ([658f150](https://github.com/smarter-sh/smarter/commit/658f150bc0149e695463eecd46b6155abb714ef2))

## [0.46.14-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.13...v0.46.14-alpha.1) (2026-11-22)

### Bug Fixes

* **settings:** group env vars by platform, subsystem and app ([1a4ed07](https://github.com/smarter-sh/smarter/commit/1a4ed078f40006ac03fff66d00e666a58957ced9))

## [0.46.13](https://github.com/smarter-sh/smarter/compare/v0.46.12...v0.46.13) (2026-11-22)

### Bug Fixes

* **account:** keep the console language and show the welcome tour once ([d9ff141](https://github.com/smarter-sh/smarter/commit/d9ff1416583df1f0312555327dcc6dba547d1588))
* **dashboard:** serve the web app manifest from the platform's origin ([58fc2a0](https://github.com/smarter-sh/smarter/commit/58fc2a0bede55246f542c02a6791d5b1836bb7b4))

## [0.46.13-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.12...v0.46.13-alpha.1) (2026-11-22)

### Bug Fixes

* **account:** keep the console language and show the welcome tour once ([d9ff141](https://github.com/smarter-sh/smarter/commit/d9ff1416583df1f0312555327dcc6dba547d1588))
* **dashboard:** serve the web app manifest from the platform's origin ([58fc2a0](https://github.com/smarter-sh/smarter/commit/58fc2a0bede55246f542c02a6791d5b1836bb7b4))

## [0.46.12](https://github.com/smarter-sh/smarter/compare/v0.46.11...v0.46.12) (2026-11-21)

### Bug Fixes

* **api:** turn each SAM resource type off with its SMARTER_ENABLE flag ([c1dc9dc](https://github.com/smarter-sh/smarter/commit/c1dc9dca877ddee1d2c67779f59d7caf7c204b36))
* **dashboard:** scope admin to staff accounts, delete through brokers ([ccb8e0c](https://github.com/smarter-sh/smarter/commit/ccb8e0c09153890678fecf6687a21acdfb973499))
* **manifest:** warn about SAM app flags that don't hold together ([647cccb](https://github.com/smarter-sh/smarter/commit/647cccb3d369ce6e784bc40471a790c2bfe9888d))

### Refactoring

* **django:** base every AppConfig on SmarterAppConfig ([7e38873](https://github.com/smarter-sh/smarter/commit/7e38873d43459b8235204bb40220156721db4c98))

## [0.46.12-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.12-alpha.1...v0.46.12-alpha.2) (2026-11-21)

### Bug Fixes

* **api:** turn each SAM resource type off with its SMARTER_ENABLE flag ([c1dc9dc](https://github.com/smarter-sh/smarter/commit/c1dc9dca877ddee1d2c67779f59d7caf7c204b36))
* **manifest:** warn about SAM app flags that don't hold together ([647cccb](https://github.com/smarter-sh/smarter/commit/647cccb3d369ce6e784bc40471a790c2bfe9888d))

### Refactoring

* **django:** base every AppConfig on SmarterAppConfig ([7e38873](https://github.com/smarter-sh/smarter/commit/7e38873d43459b8235204bb40220156721db4c98))

## [0.46.12-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.11...v0.46.12-alpha.1) (2026-11-21)

### Bug Fixes

* **dashboard:** scope admin to staff accounts, delete through brokers ([ccb8e0c](https://github.com/smarter-sh/smarter/commit/ccb8e0c09153890678fecf6687a21acdfb973499))

## [0.46.11](https://github.com/smarter-sh/smarter/compare/v0.46.10...v0.46.11) (2026-11-21)

### Bug Fixes

* **settings:** harden security, quiet the logs and prune dependencies ([f2432df](https://github.com/smarter-sh/smarter/commit/f2432df489338e0d8a71159d50ab8b42dfa43101))

## [0.46.11-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.10...v0.46.11-alpha.1) (2026-11-21)

### Bug Fixes

* **settings:** harden security, quiet the logs and prune dependencies ([f2432df](https://github.com/smarter-sh/smarter/commit/f2432df489338e0d8a71159d50ab8b42dfa43101))

## [0.46.10](https://github.com/smarter-sh/smarter/compare/v0.46.9...v0.46.10) (2026-11-21)

### Bug Fixes

* bump smarter-console to v1.1.13 ([1859986](https://github.com/smarter-sh/smarter/commit/1859986f9f2785742538846972f808a41936c5b1))
* **django:** adopt django 6 csp, unique constraints, and storages ([c81f3a6](https://github.com/smarter-sh/smarter/commit/c81f3a650448aeee55588a54e8d17daeab251bf1))
* **logging:** fix stale ready-message test, drop decorative prefixes ([cc0c07e](https://github.com/smarter-sh/smarter/commit/cc0c07e351aeefaba16dfedf0da1c3c496d5c6ff))
* **orchestrator:** send a signal at each step of a run's lifecycle ([d71cd1b](https://github.com/smarter-sh/smarter/commit/d71cd1b0955e74e3b8edc5df6ef5ef196cfbb9ee))
* **provider:** treat account-policy 403s as inconclusive ([0a39ea1](https://github.com/smarter-sh/smarter/commit/0a39ea1b3b3980652c18f0767db8ec668f4de7c2)), closes [smarter-sh/smarter#1024](https://github.com/smarter-sh/smarter/issues/1024) [#1024](https://github.com/smarter-sh/smarter/issues/1024)
* **secret:** send each secret event once, and receive secret_edited ([3481b61](https://github.com/smarter-sh/smarter/commit/3481b6129b2001b323bdef8fbc02195972a710a4))
* **settings:** let user-defined django settings supersede every module ([01b8919](https://github.com/smarter-sh/smarter/commit/01b8919e6841c66f1083e7fd29d5fd3ed667b48d))
* **signals:** add receivers for four signals that had none ([8409542](https://github.com/smarter-sh/smarter/commit/840954284ffb8f9db25166a7b7596f5bfc0ecfb0))

### Refactoring

* consolidate formatted_log_prefix logic ([8035827](https://github.com/smarter-sh/smarter/commit/8035827292666fab5e6e1c7d9d43c59cd34437f4))
* **logging:** let the logger write each message's origin prefix ([8039a46](https://github.com/smarter-sh/smarter/commit/8039a4677516c0876b7dae8fcfbd94f6ec9edc76))
* **logging:** remove hand-written origins from log messages ([5603401](https://github.com/smarter-sh/smarter/commit/5603401228a99034f88e88b5c9fb8873c8c86018))
* **prompt:** remove the prompt_handler_console_output signal ([a8ef86d](https://github.com/smarter-sh/smarter/commit/a8ef86da1fe42513be878af3cf9722d2cbfdca09))
* **signals:** log each signaled event once, from its receiver ([cd34249](https://github.com/smarter-sh/smarter/commit/cd342496dbe3b182aca627e6fd3c2b145f4da94c))

## [0.46.10-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.46.10-alpha.4...v0.46.10-alpha.5) (2026-11-21)

### Bug Fixes

* bump smarter-console to v1.1.13 ([1859986](https://github.com/smarter-sh/smarter/commit/1859986f9f2785742538846972f808a41936c5b1))

## [0.46.10-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.46.10-alpha.3...v0.46.10-alpha.4) (2026-11-21)

### Bug Fixes

* **settings:** let user-defined django settings supersede every module ([01b8919](https://github.com/smarter-sh/smarter/commit/01b8919e6841c66f1083e7fd29d5fd3ed667b48d))

## [0.46.10-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.46.10-alpha.2...v0.46.10-alpha.3) (2026-11-21)

### Bug Fixes

* **django:** adopt django 6 csp, unique constraints, and storages ([c81f3a6](https://github.com/smarter-sh/smarter/commit/c81f3a650448aeee55588a54e8d17daeab251bf1))

## [0.46.10-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.10-alpha.1...v0.46.10-alpha.2) (2026-11-21)

### Bug Fixes

* **logging:** fix stale ready-message test, drop decorative prefixes ([cc0c07e](https://github.com/smarter-sh/smarter/commit/cc0c07e351aeefaba16dfedf0da1c3c496d5c6ff))
* **orchestrator:** send a signal at each step of a run's lifecycle ([d71cd1b](https://github.com/smarter-sh/smarter/commit/d71cd1b0955e74e3b8edc5df6ef5ef196cfbb9ee))
* **secret:** send each secret event once, and receive secret_edited ([3481b61](https://github.com/smarter-sh/smarter/commit/3481b6129b2001b323bdef8fbc02195972a710a4))
* **signals:** add receivers for four signals that had none ([8409542](https://github.com/smarter-sh/smarter/commit/840954284ffb8f9db25166a7b7596f5bfc0ecfb0))

### Refactoring

* consolidate formatted_log_prefix logic ([8035827](https://github.com/smarter-sh/smarter/commit/8035827292666fab5e6e1c7d9d43c59cd34437f4))
* **logging:** let the logger write each message's origin prefix ([8039a46](https://github.com/smarter-sh/smarter/commit/8039a4677516c0876b7dae8fcfbd94f6ec9edc76))
* **logging:** remove hand-written origins from log messages ([5603401](https://github.com/smarter-sh/smarter/commit/5603401228a99034f88e88b5c9fb8873c8c86018))
* **prompt:** remove the prompt_handler_console_output signal ([a8ef86d](https://github.com/smarter-sh/smarter/commit/a8ef86da1fe42513be878af3cf9722d2cbfdca09))
* **signals:** log each signaled event once, from its receiver ([cd34249](https://github.com/smarter-sh/smarter/commit/cd342496dbe3b182aca627e6fd3c2b145f4da94c))

## [0.46.10-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.9...v0.46.10-alpha.1) (2026-11-21)

### Bug Fixes

* **provider:** treat account-policy 403s as inconclusive ([0a39ea1](https://github.com/smarter-sh/smarter/commit/0a39ea1b3b3980652c18f0767db8ec668f4de7c2)), closes [smarter-sh/smarter#1024](https://github.com/smarter-sh/smarter/issues/1024) [#1024](https://github.com/smarter-sh/smarter/issues/1024)

## [0.46.9](https://github.com/smarter-sh/smarter/compare/v0.46.8...v0.46.9) (2026-11-19)

### Bug Fixes

- broken css on youtube page ([929216a](https://github.com/smarter-sh/smarter/commit/929216a2fde5382e753cbb2c2ffec25fbf81ab91))

## [0.46.9-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.8...v0.46.9-alpha.1) (2026-11-19)

### Bug Fixes

- broken css on youtube page ([929216a](https://github.com/smarter-sh/smarter/commit/929216a2fde5382e753cbb2c2ffec25fbf81ab91))

## [0.46.8](https://github.com/smarter-sh/smarter/compare/v0.46.7...v0.46.8) (2026-11-19)

### Bug Fixes

- **api:** answer client errors with 400 and unknown errors with 500 ([0d6ca4f](https://github.com/smarter-sh/smarter/commit/0d6ca4f535081687c109379e74b92acc3cef52ff))
- **api:** keep plugin server errors at 500, manifest errors at 400 ([395423e](https://github.com/smarter-sh/smarter/commit/395423e479fe98d7148208b56fa77ca6bf79508d))
- close cache getter type gaps and a provider serializer bug ([2e08cdd](https://github.com/smarter-sh/smarter/commit/2e08cdd36c3dfef5473bcc22c4299f1c2fe00b14))
- **drf:** log an uninitialized SmarterAuthToken manifest at DEBUG, not WARNING ([b1a5d89](https://github.com/smarter-sh/smarter/commit/b1a5d897c6588228380068901cf6c6d13a7f8f11)), closes [#1015](https://github.com/smarter-sh/smarter/issues/1015) [#1020](https://github.com/smarter-sh/smarter/issues/1020)

## [0.46.8-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.8-alpha.1...v0.46.8-alpha.2) (2026-11-19)

### Bug Fixes

- **api:** answer client errors with 400 and unknown errors with 500 ([0d6ca4f](https://github.com/smarter-sh/smarter/commit/0d6ca4f535081687c109379e74b92acc3cef52ff))
- **api:** keep plugin server errors at 500, manifest errors at 400 ([395423e](https://github.com/smarter-sh/smarter/commit/395423e479fe98d7148208b56fa77ca6bf79508d))
- close cache getter type gaps and a provider serializer bug ([2e08cdd](https://github.com/smarter-sh/smarter/commit/2e08cdd36c3dfef5473bcc22c4299f1c2fe00b14))

## [0.46.8-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.7...v0.46.8-alpha.1) (2026-11-18)

### Bug Fixes

- **drf:** log an uninitialized SmarterAuthToken manifest at DEBUG, not WARNING ([b1a5d89](https://github.com/smarter-sh/smarter/commit/b1a5d897c6588228380068901cf6c6d13a7f8f11)), closes [#1015](https://github.com/smarter-sh/smarter/issues/1015) [#1020](https://github.com/smarter-sh/smarter/issues/1020)

## [0.46.7](https://github.com/smarter-sh/smarter/compare/v0.46.6...v0.46.7) (2026-11-18)

### Bug Fixes

- **account:** authenticate to account manager and remove mailchimp ([36cbf82](https://github.com/smarter-sh/smarter/commit/36cbf8210f7dd09c68124e3f29d008031046711e))
- **account:** set the root account's share scope through its relation ([32e0015](https://github.com/smarter-sh/smarter/commit/32e0015fa89c108819102de10f05497fff533894))

### Refactoring

- **manifest:** give brokers manifest data instead of a SAMLoader ([5458727](https://github.com/smarter-sh/smarter/commit/5458727990c292ad000caae0eec26349c2844aa0))
- **manifest:** parse manifests without SAMLoader outside brokers ([ea87bb9](https://github.com/smarter-sh/smarter/commit/ea87bb982469b60d77afc1ce1a51c68e6a6c8264))
- **manifest:** remove SAMLoader ([61e152b](https://github.com/smarter-sh/smarter/commit/61e152b0e4ed368983cffecebc1e3e5a2e06e371))

## [0.46.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.6...v0.46.7-alpha.1) (2026-11-18)

### Bug Fixes

- **account:** authenticate to account manager and remove mailchimp ([36cbf82](https://github.com/smarter-sh/smarter/commit/36cbf8210f7dd09c68124e3f29d008031046711e))
- **account:** set the root account's share scope through its relation ([32e0015](https://github.com/smarter-sh/smarter/commit/32e0015fa89c108819102de10f05497fff533894))

## [0.46.6](https://github.com/smarter-sh/smarter/compare/v0.46.5...v0.46.6) (2026-11-17)

### Bug Fixes

- **account:** log a missing broker instance at DEBUG, not WARNING ([f6e25ba](https://github.com/smarter-sh/smarter/commit/f6e25ba46096fda51f6899a553d06ff65d8c94b4)), closes [#1017](https://github.com/smarter-sh/smarter/issues/1017) [#1017](https://github.com/smarter-sh/smarter/issues/1017) [#1016](https://github.com/smarter-sh/smarter/issues/1016) [#985](https://github.com/smarter-sh/smarter/issues/985)
- **django:** log a missing row in get_object_by_locator() as a WARNING ([f5650ac](https://github.com/smarter-sh/smarter/commit/f5650acb6341a2b540f620ffccfc86b39439a487)), closes [#1014](https://github.com/smarter-sh/smarter/issues/1014)
- **llmtool:** log a plugin's tool result at DEBUG, and only its length at INFO ([8581a1c](https://github.com/smarter-sh/smarter/commit/8581a1c95d31b8676912a3e45ce967c5923260fd)), closes [#1013](https://github.com/smarter-sh/smarter/issues/1013)

## [0.46.6-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.6-alpha.1...v0.46.6-alpha.2) (2026-11-17)

### Bug Fixes

- **account:** log a missing broker instance at DEBUG, not WARNING ([f6e25ba](https://github.com/smarter-sh/smarter/commit/f6e25ba46096fda51f6899a553d06ff65d8c94b4)), closes [#1017](https://github.com/smarter-sh/smarter/issues/1017) [#1017](https://github.com/smarter-sh/smarter/issues/1017) [#1016](https://github.com/smarter-sh/smarter/issues/1016) [#985](https://github.com/smarter-sh/smarter/issues/985)

## [0.46.6-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.5...v0.46.6-alpha.1) (2026-11-17)

### Bug Fixes

- **django:** log a missing row in get_object_by_locator() as a WARNING ([f5650ac](https://github.com/smarter-sh/smarter/commit/f5650acb6341a2b540f620ffccfc86b39439a487)), closes [#1014](https://github.com/smarter-sh/smarter/issues/1014)
- **llmtool:** log a plugin's tool result at DEBUG, and only its length at INFO ([8581a1c](https://github.com/smarter-sh/smarter/commit/8581a1c95d31b8676912a3e45ce967c5923260fd)), closes [#1013](https://github.com/smarter-sh/smarter/issues/1013)

## [0.46.5](https://github.com/smarter-sh/smarter/compare/v0.46.4...v0.46.5) (2026-11-16)

### Bug Fixes

- **journal:** show the reply of LLMClient prompts in the admin ([d54d7b3](https://github.com/smarter-sh/smarter/commit/d54d7b3a3638aa8b02b7ac95b84040cc6ede1328))

## [0.46.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.4...v0.46.5-alpha.1) (2026-11-16)

### Bug Fixes

- **journal:** show the reply of LLMClient prompts in the admin ([d54d7b3](https://github.com/smarter-sh/smarter/commit/d54d7b3a3638aa8b02b7ac95b84040cc6ede1328))

## [0.46.4](https://github.com/smarter-sh/smarter/compare/v0.46.3...v0.46.4) (2026-11-16)

### Bug Fixes

- **journal:** save request bodies, show prompt and reply in admin ([6097d98](https://github.com/smarter-sh/smarter/commit/6097d9815029fb577518927a4aff102f58af0dcc))

## [0.46.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.3...v0.46.4-alpha.1) (2026-11-16)

### Bug Fixes

- **journal:** save request bodies, show prompt and reply in admin ([6097d98](https://github.com/smarter-sh/smarter/commit/6097d9815029fb577518927a4aff102f58af0dcc))

## [0.46.3](https://github.com/smarter-sh/smarter/compare/v0.46.2...v0.46.3) (2026-11-15)

### Bug Fixes

- **logging:** mask the session_key in the uvicorn access log ([409b100](https://github.com/smarter-sh/smarter/commit/409b100499bcaa2db7b07a931ee4b9cf7e657ce1)), closes [#1000](https://github.com/smarter-sh/smarter/issues/1000)
- **prompt:** prune old prompt history daily, split the settings module ([97bba53](https://github.com/smarter-sh/smarter/commit/97bba53e0b7e103558419e9f25e26c283eebf373))

## [0.46.3-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.3-alpha.1...v0.46.3-alpha.2) (2026-11-15)

### Bug Fixes

- **prompt:** prune old prompt history daily, split the settings module ([97bba53](https://github.com/smarter-sh/smarter/commit/97bba53e0b7e103558419e9f25e26c283eebf373))

## [0.46.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.2...v0.46.3-alpha.1) (2026-11-15)

### Bug Fixes

- **logging:** mask the session_key in the uvicorn access log ([409b100](https://github.com/smarter-sh/smarter/commit/409b100499bcaa2db7b07a931ee4b9cf7e657ce1)), closes [#1000](https://github.com/smarter-sh/smarter/issues/1000)

## [0.46.2](https://github.com/smarter-sh/smarter/compare/v0.46.1...v0.46.2) (2026-11-15)

### Bug Fixes

- **helm:** migrate in a pre-upgrade job before new pods take requests ([4e39d91](https://github.com/smarter-sh/smarter/commit/4e39d9198860fed56871cd0b5707a462f6d1b143)), closes [#1007](https://github.com/smarter-sh/smarter/issues/1007)
- **journal:** prune orphaned blobs and stop retrying deleted rows ([90cd4d5](https://github.com/smarter-sh/smarter/commit/90cd4d5b5d370f4e7c4fce79c2601d923682b04f))
- **prompt:** mask the session_key in the urls that handle_chat_config_invoked() and SmarterSecurityMiddleware log ([115dd82](https://github.com/smarter-sh/smarter/commit/115dd82f39436a05c6e0a84f8161c834fa11200c)), closes [#1004](https://github.com/smarter-sh/smarter/issues/1004) [#1000](https://github.com/smarter-sh/smarter/issues/1000)

### Refactoring

- **llmclient:** share in-process prompting across apps ([1806c86](https://github.com/smarter-sh/smarter/commit/1806c86e391c2f40f2896f6d1bbee23e86dddd13))

### Performance

- **journal:** write entries in Celery and deduplicate their documents ([5619c6b](https://github.com/smarter-sh/smarter/commit/5619c6b40d9578b107fb83e7b78e4aad5d887505))

## [0.46.2-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.46.2-alpha.3...v0.46.2-alpha.4) (2026-11-15)

### Bug Fixes

- **helm:** migrate in a pre-upgrade job before new pods take requests ([4e39d91](https://github.com/smarter-sh/smarter/commit/4e39d9198860fed56871cd0b5707a462f6d1b143)), closes [#1007](https://github.com/smarter-sh/smarter/issues/1007)

## [0.46.2-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.46.2-alpha.2...v0.46.2-alpha.3) (2026-11-15)

### Bug Fixes

- **prompt:** mask the session_key in the urls that handle_chat_config_invoked() and SmarterSecurityMiddleware log ([115dd82](https://github.com/smarter-sh/smarter/commit/115dd82f39436a05c6e0a84f8161c834fa11200c)), closes [#1004](https://github.com/smarter-sh/smarter/issues/1004) [#1000](https://github.com/smarter-sh/smarter/issues/1000)

## [0.46.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.2-alpha.1...v0.46.2-alpha.2) (2026-11-15)

### Bug Fixes

- **journal:** prune orphaned blobs and stop retrying deleted rows ([90cd4d5](https://github.com/smarter-sh/smarter/commit/90cd4d5b5d370f4e7c4fce79c2601d923682b04f))

## [0.46.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.1...v0.46.2-alpha.1) (2026-11-15)

### Refactoring

- **llmclient:** share in-process prompting across apps ([1806c86](https://github.com/smarter-sh/smarter/commit/1806c86e391c2f40f2896f6d1bbee23e86dddd13))

### Performance

- **journal:** write entries in Celery and deduplicate their documents ([5619c6b](https://github.com/smarter-sh/smarter/commit/5619c6b40d9578b107fb83e7b78e4aad5d887505))

## [0.46.1](https://github.com/smarter-sh/smarter/compare/v0.46.0...v0.46.1) (2026-11-15)

### Bug Fixes

- bump smarter-console to v1.1.12 ([699391c](https://github.com/smarter-sh/smarter/commit/699391c0f84f1f69f1abc02253cbe0490b589259))

## [0.46.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.46.0...v0.46.1-alpha.1) (2026-11-15)

### Bug Fixes

- bump smarter-console to v1.1.12 ([699391c](https://github.com/smarter-sh/smarter/commit/699391c0f84f1f69f1abc02253cbe0490b589259))

## [0.46.0](https://github.com/smarter-sh/smarter/compare/v0.45.2...v0.46.0) (2026-11-14)

### Features

- **account:** add an account administrator role to user profiles ([8f41e9b](https://github.com/smarter-sh/smarter/commit/8f41e9bcfdfa03935cf4b1af0a69b2a419d7535b))
- **account:** add an account hierarchy with resource sharing ([4727aa1](https://github.com/smarter-sh/smarter/commit/4727aa1e2f4236bee6fdccd5f7189d960933ff2f))
- **account:** add passwordSecret to the User manifest ([79c81b6](https://github.com/smarter-sh/smarter/commit/79c81b65c7f7ba95367adf7a80ac8b43839a3aa0))
- **account:** let a repository's owners.yaml say who owns each folder ([ce36b37](https://github.com/smarter-sh/smarter/commit/ce36b374cde80629f19162d4cc7d0b77b4c5e537))
- **account:** list a user's account memberships in the User manifest ([637105e](https://github.com/smarter-sh/smarter/commit/637105eceaa6d8c2e289779ca84989d4699bb326))
- **orchestrator:** run orchestrations, sequential and parallel ([d144957](https://github.com/smarter-sh/smarter/commit/d14495711ea7a9aacd6425f6de970caf099726af))

### Bug Fixes

- **account:** create an account with its manifest's account number ([29491e1](https://github.com/smarter-sh/smarter/commit/29491e1cd48ee7df59a8fda94051fd6eff0ab4c0))
- **account:** let account admins who aren't staff create api keys ([2427861](https://github.com/smarter-sh/smarter/commit/2427861381686d5ab49b2d68a73fce11deaf5fa6))
- **account:** load an organization into its own accounts ([3b31966](https://github.com/smarter-sh/smarter/commit/3b31966dc58028798e2d2a2b5b0f91ec8dabf89c))
- **account:** make a newly joined account the user's default ([bac4e6f](https://github.com/smarter-sh/smarter/commit/bac4e6fbfe17ae75900f51e3f18dfd8ee06ca6b7))
- **account:** never make an account's administrator a superuser ([a2c849c](https://github.com/smarter-sh/smarter/commit/a2c849cd0d1ef439e9f1344259227af57ccf65e9))
- **account:** resolve guardrails by account tree, skip owned deploys ([d3a61ba](https://github.com/smarter-sh/smarter/commit/d3a61ba1772c8edf03c14c79b7756024a6c0c314))
- **account:** staff administer only the accounts they belong to ([d2ca953](https://github.com/smarter-sh/smarter/commit/d2ca9533a75ef75a70a12eaac0ffaecff2135abd))
- **account:** stop tests leaving orphaned accounts and superusers ([5ab7ed5](https://github.com/smarter-sh/smarter/commit/5ab7ed5b741518338093102bc0ad156ac9d87984))
- **dashboard:** stop stream_user_logs() logging the username and the full chat session key ([b7aa505](https://github.com/smarter-sh/smarter/commit/b7aa50529907ef109f72b048bd4a5e7c3336ba20)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1000](https://github.com/smarter-sh/smarter/issues/1000)
- **dashboard:** stop stream_user_logs() logging the username and the full chat session key ([b6c92e5](https://github.com/smarter-sh/smarter/commit/b6c92e5b28648b57e96956a6e77ead089994463b)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1000](https://github.com/smarter-sh/smarter/issues/1000)
- **docs:** use docs.smarter.sh for the sitemap and canonical links ([f61e018](https://github.com/smarter-sh/smarter/commit/f61e018ddcd12c660fd83f4dcad49aba60908b47))
- **llmtool:** find a plugin by name in its account, not its admin's ([07b7483](https://github.com/smarter-sh/smarter/commit/07b7483ec452283b93dfd04067fad948d8c23fc1))
- **orchestrator:** list the user's runs of an orchestrator ([b22c6cb](https://github.com/smarter-sh/smarter/commit/b22c6cbb3dcabfec9f2f606ecc0b2e02d42257bc))
- **orchestrator:** run supervisor and router orchestrations ([61c4a01](https://github.com/smarter-sh/smarter/commit/61c4a01da148849249e897d44bcdeb3976888283))

### Refactoring

- **account:** switch stackademy to its renamed resources ([76fabbc](https://github.com/smarter-sh/smarter/commit/76fabbc52fd8e53a13980ae891a76bc305235016))

## [0.46.0](https://github.com/smarter-sh/smarter/compare/v0.45.2...v0.46.0) (2026-11-14)

### Features

- **account:** add an account administrator role to user profiles ([8f41e9b](https://github.com/smarter-sh/smarter/commit/8f41e9bcfdfa03935cf4b1af0a69b2a419d7535b))
- **account:** add an account hierarchy with resource sharing ([4727aa1](https://github.com/smarter-sh/smarter/commit/4727aa1e2f4236bee6fdccd5f7189d960933ff2f))
- **account:** add passwordSecret to the User manifest ([79c81b6](https://github.com/smarter-sh/smarter/commit/79c81b65c7f7ba95367adf7a80ac8b43839a3aa0))
- **account:** let a repository's owners.yaml say who owns each folder ([ce36b37](https://github.com/smarter-sh/smarter/commit/ce36b374cde80629f19162d4cc7d0b77b4c5e537))
- **account:** list a user's account memberships in the User manifest ([637105e](https://github.com/smarter-sh/smarter/commit/637105eceaa6d8c2e289779ca84989d4699bb326))
- **orchestrator:** run orchestrations, sequential and parallel ([d144957](https://github.com/smarter-sh/smarter/commit/d14495711ea7a9aacd6425f6de970caf099726af))

### Bug Fixes

- **account:** create an account with its manifest's account number ([29491e1](https://github.com/smarter-sh/smarter/commit/29491e1cd48ee7df59a8fda94051fd6eff0ab4c0))
- **account:** let account admins who aren't staff create api keys ([2427861](https://github.com/smarter-sh/smarter/commit/2427861381686d5ab49b2d68a73fce11deaf5fa6))
- **account:** load an organization into its own accounts ([3b31966](https://github.com/smarter-sh/smarter/commit/3b31966dc58028798e2d2a2b5b0f91ec8dabf89c))
- **account:** make a newly joined account the user's default ([bac4e6f](https://github.com/smarter-sh/smarter/commit/bac4e6fbfe17ae75900f51e3f18dfd8ee06ca6b7))
- **account:** never make an account's administrator a superuser ([a2c849c](https://github.com/smarter-sh/smarter/commit/a2c849cd0d1ef439e9f1344259227af57ccf65e9))
- **account:** resolve guardrails by account tree, skip owned deploys ([d3a61ba](https://github.com/smarter-sh/smarter/commit/d3a61ba1772c8edf03c14c79b7756024a6c0c314))
- **account:** staff administer only the accounts they belong to ([d2ca953](https://github.com/smarter-sh/smarter/commit/d2ca9533a75ef75a70a12eaac0ffaecff2135abd))
- **account:** stop tests leaving orphaned accounts and superusers ([5ab7ed5](https://github.com/smarter-sh/smarter/commit/5ab7ed5b741518338093102bc0ad156ac9d87984))
- **dashboard:** stop stream_user_logs() logging the username and the full chat session key ([b7aa505](https://github.com/smarter-sh/smarter/commit/b7aa50529907ef109f72b048bd4a5e7c3336ba20)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1000](https://github.com/smarter-sh/smarter/issues/1000)
- **dashboard:** stop stream_user_logs() logging the username and the full chat session key ([b6c92e5](https://github.com/smarter-sh/smarter/commit/b6c92e5b28648b57e96956a6e77ead089994463b)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1000](https://github.com/smarter-sh/smarter/issues/1000)
- **docs:** use docs.smarter.sh for the sitemap and canonical links ([f61e018](https://github.com/smarter-sh/smarter/commit/f61e018ddcd12c660fd83f4dcad49aba60908b47))
- **llmtool:** find a plugin by name in its account, not its admin's ([07b7483](https://github.com/smarter-sh/smarter/commit/07b7483ec452283b93dfd04067fad948d8c23fc1))
- **orchestrator:** list the user's runs of an orchestrator ([b22c6cb](https://github.com/smarter-sh/smarter/commit/b22c6cbb3dcabfec9f2f606ecc0b2e02d42257bc))
- **orchestrator:** run supervisor and router orchestrations ([61c4a01](https://github.com/smarter-sh/smarter/commit/61c4a01da148849249e897d44bcdeb3976888283))

### Refactoring

- **account:** switch stackademy to its renamed resources ([76fabbc](https://github.com/smarter-sh/smarter/commit/76fabbc52fd8e53a13980ae891a76bc305235016))

## [0.46.0-alpha.17](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.16...v0.46.0-alpha.17) (2026-11-14)

### Bug Fixes

- **orchestrator:** list the user's runs of an orchestrator ([b22c6cb](https://github.com/smarter-sh/smarter/commit/b22c6cbb3dcabfec9f2f606ecc0b2e02d42257bc))

## [0.46.0-alpha.16](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.15...v0.46.0-alpha.16) (2026-11-14)

### Bug Fixes

- **orchestrator:** run supervisor and router orchestrations ([61c4a01](https://github.com/smarter-sh/smarter/commit/61c4a01da148849249e897d44bcdeb3976888283))

## [0.46.0-alpha.15](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.14...v0.46.0-alpha.15) (2026-11-14)

### Features

- **orchestrator:** run orchestrations, sequential and parallel ([d144957](https://github.com/smarter-sh/smarter/commit/d14495711ea7a9aacd6425f6de970caf099726af))

## [0.46.0-alpha.14](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.13...v0.46.0-alpha.14) (2026-11-14)

### Bug Fixes

- **llmtool:** find a plugin by name in its account, not its admin's ([07b7483](https://github.com/smarter-sh/smarter/commit/07b7483ec452283b93dfd04067fad948d8c23fc1))

## [0.46.0-alpha.13](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.12...v0.46.0-alpha.13) (2026-11-14)

### Bug Fixes

- **account:** make a newly joined account the user's default ([bac4e6f](https://github.com/smarter-sh/smarter/commit/bac4e6fbfe17ae75900f51e3f18dfd8ee06ca6b7))

## [0.46.0-alpha.12](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.11...v0.46.0-alpha.12) (2026-11-14)

### Bug Fixes

- **account:** staff administer only the accounts they belong to ([d2ca953](https://github.com/smarter-sh/smarter/commit/d2ca9533a75ef75a70a12eaac0ffaecff2135abd))

## [0.46.0-alpha.11](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.10...v0.46.0-alpha.11) (2026-11-14)

### Bug Fixes

- **account:** let account admins who aren't staff create api keys ([2427861](https://github.com/smarter-sh/smarter/commit/2427861381686d5ab49b2d68a73fce11deaf5fa6))

## [0.46.0-alpha.10](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.9...v0.46.0-alpha.10) (2026-11-14)

### Bug Fixes

- **account:** resolve guardrails by account tree, skip owned deploys ([d3a61ba](https://github.com/smarter-sh/smarter/commit/d3a61ba1772c8edf03c14c79b7756024a6c0c314))

## [0.46.0-alpha.9](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.8...v0.46.0-alpha.9) (2026-11-14)

### Bug Fixes

- **account:** load an organization into its own accounts ([3b31966](https://github.com/smarter-sh/smarter/commit/3b31966dc58028798e2d2a2b5b0f91ec8dabf89c))

## [0.46.0-alpha.8](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.7...v0.46.0-alpha.8) (2026-11-14)

### Bug Fixes

- **account:** create an account with its manifest's account number ([29491e1](https://github.com/smarter-sh/smarter/commit/29491e1cd48ee7df59a8fda94051fd6eff0ab4c0))

## [0.46.0-alpha.7](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.6...v0.46.0-alpha.7) (2026-11-14)

### Features

- **account:** let a repository's owners.yaml say who owns each folder ([ce36b37](https://github.com/smarter-sh/smarter/commit/ce36b374cde80629f19162d4cc7d0b77b4c5e537))

### Bug Fixes

- **account:** never make an account's administrator a superuser ([a2c849c](https://github.com/smarter-sh/smarter/commit/a2c849cd0d1ef439e9f1344259227af57ccf65e9))

## [0.46.0-alpha.6](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.5...v0.46.0-alpha.6) (2026-11-14)

### Features

- **account:** add passwordSecret to the User manifest ([79c81b6](https://github.com/smarter-sh/smarter/commit/79c81b65c7f7ba95367adf7a80ac8b43839a3aa0))
- **account:** list a user's account memberships in the User manifest ([637105e](https://github.com/smarter-sh/smarter/commit/637105eceaa6d8c2e289779ca84989d4699bb326))

## [0.46.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.4...v0.46.0-alpha.5) (2026-11-14)

### Bug Fixes

- **dashboard:** stop stream_user_logs() logging the username and the full chat session key ([b7aa505](https://github.com/smarter-sh/smarter/commit/b7aa50529907ef109f72b048bd4a5e7c3336ba20)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1000](https://github.com/smarter-sh/smarter/issues/1000)

## [0.46.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.3...v0.46.0-alpha.4) (2026-11-14)

### Bug Fixes

- **dashboard:** stop stream_user_logs() logging the username and the full chat session key ([b6c92e5](https://github.com/smarter-sh/smarter/commit/b6c92e5b28648b57e96956a6e77ead089994463b)), closes [#1001](https://github.com/smarter-sh/smarter/issues/1001) [#1000](https://github.com/smarter-sh/smarter/issues/1000)

## [0.46.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.2...v0.46.0-alpha.3) (2026-11-14)

### Features

- **account:** add an account administrator role to user profiles ([8f41e9b](https://github.com/smarter-sh/smarter/commit/8f41e9bcfdfa03935cf4b1af0a69b2a419d7535b))

### Refactoring

- **account:** switch stackademy to its renamed resources ([76fabbc](https://github.com/smarter-sh/smarter/commit/76fabbc52fd8e53a13980ae891a76bc305235016))

## [0.46.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.46.0-alpha.1...v0.46.0-alpha.2) (2026-11-14)

### Bug Fixes

- **account:** stop tests leaving orphaned accounts and superusers ([5ab7ed5](https://github.com/smarter-sh/smarter/commit/5ab7ed5b741518338093102bc0ad156ac9d87984))

## [0.46.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.45.3-alpha.1...v0.46.0-alpha.1) (2026-11-14)

### Features

- **account:** add an account hierarchy with resource sharing ([4727aa1](https://github.com/smarter-sh/smarter/commit/4727aa1e2f4236bee6fdccd5f7189d960933ff2f))
