# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.43.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.43.2...v0.43.3-alpha.1) (2026-11-08)

### Bug Fixes

- **waffle:** log a database outage in switch_is_active() as one warning line ([ff7d343](https://github.com/smarter-sh/smarter/commit/ff7d343d55287c1fb9d8f30403c6261ee34f5103)), closes [#951](https://github.com/smarter-sh/smarter/issues/951)

## [0.43.2](https://github.com/smarter-sh/smarter/compare/v0.43.1...v0.43.2) (2026-11-08)

### Bug Fixes

- bump smarter-console to v1.0.18 ([37b42c5](https://github.com/smarter-sh/smarter/commit/37b42c57be8653485d4c34eeac16985a25739c4d))
- **celery:** set RedBeat's url and options where RedBeat reads them ([f26f71d](https://github.com/smarter-sh/smarter/commit/f26f71db3d6a1b46c7b66a3585830e8470703c36))
- **plugin:** log the manifest-not-initialized broker state at debug ([bdf69d8](https://github.com/smarter-sh/smarter/commit/bdf69d895735d8523eec3bf004c72c0470ee357b))

## [0.43.2-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.43.2-alpha.2...v0.43.2-alpha.3) (2026-11-08)

### Bug Fixes

- bump smarter-console to v1.0.18 ([37b42c5](https://github.com/smarter-sh/smarter/commit/37b42c57be8653485d4c34eeac16985a25739c4d))

## [0.43.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.43.2-alpha.1...v0.43.2-alpha.2) (2026-11-08)

### Bug Fixes

- **plugin:** log the manifest-not-initialized broker state at debug ([bdf69d8](https://github.com/smarter-sh/smarter/commit/bdf69d895735d8523eec3bf004c72c0470ee357b))

## [0.43.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.43.1...v0.43.2-alpha.1) (2026-11-08)

### Bug Fixes

- **celery:** set RedBeat's url and options where RedBeat reads them ([f26f71d](https://github.com/smarter-sh/smarter/commit/f26f71db3d6a1b46c7b66a3585830e8470703c36))

## [0.43.1](https://github.com/smarter-sh/smarter/compare/v0.43.0...v0.43.1) (2026-11-08)

### Bug Fixes

- **helm:** stop running the api twice under its old name, smarter ([08a25eb](https://github.com/smarter-sh/smarter/commit/08a25eb7cfb9086c24c4c7605f5b4e2b4dbfa604))

### Refactoring

- **helm:** rename the api's templates from -app to -api ([2fdb2d3](https://github.com/smarter-sh/smarter/commit/2fdb2d326292dc8a8632646b204af42f7d169fa7))

## [0.43.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.43.0...v0.43.1-alpha.1) (2026-11-08)

### Bug Fixes

- **helm:** stop running the api twice under its old name, smarter ([08a25eb](https://github.com/smarter-sh/smarter/commit/08a25eb7cfb9086c24c4c7605f5b4e2b4dbfa604))

### Refactoring

- **helm:** rename the api's templates from -app to -api ([2fdb2d3](https://github.com/smarter-sh/smarter/commit/2fdb2d326292dc8a8632646b204af42f7d169fa7))

## [0.43.0](https://github.com/smarter-sh/smarter/compare/v0.42.10...v0.43.0) (2026-11-08)

### Features

- **api:** add the web console session api, GET /api/web/session/ ([5f48fa1](https://github.com/smarter-sh/smarter/commit/5f48fa111b7c966075754b5cfd5d4fba0b3c6117))
- **react:** add @smarter/console, the single-page web console ([6591148](https://github.com/smarter-sh/smarter/commit/659114897e502d78e5163cc837ec915b5bf97ac4))

### Bug Fixes

- **account:** send a test account's generated admin no welcome email ([026477b](https://github.com/smarter-sh/smarter/commit/026477bbdf9070c155224c654b04dfd7613a4791))
- **account:** show the console in the welcome email's graphic ([93f0b93](https://github.com/smarter-sh/smarter/commit/93f0b93bfdb855f3f01b26c8a3a08aa9a3436d21))
- **account:** verify email on sign-up, move account pages to console ([e96fc95](https://github.com/smarter-sh/smarter/commit/e96fc95754ee57504db979850b13a2897517486a))
- **console:** remove dead pages and close three sign-in security holes ([ab94076](https://github.com/smarter-sh/smarter/commit/ab94076fa0691715fa446e89fa6a1604104da2a2))
- **dashboard:** give Budgets a read rule in the resource api ([3f5e6ac](https://github.com/smarter-sh/smarter/commit/3f5e6ac8d738191ac5ca187ad439253bf90ef46a))
- **dashboard:** serve the console without its splash to visitors ([6e654fa](https://github.com/smarter-sh/smarter/commit/6e654fa080a70ea5e032b6af8595ddc9a9fbf8a4))
- **mcpserver:** index smarter-console, and list its contract copies ([7477974](https://github.com/smarter-sh/smarter/commit/7477974e8be99095f2c8cae57760422482c6bcf6))
- **prompt:** log a config request for a deleted LLMClient below ERROR ([b4c4d90](https://github.com/smarter-sh/smarter/commit/b4c4d902fa65e745eac74542e2a872b9e74ae0f3)), closes [#897](https://github.com/smarter-sh/smarter/issues/897)
- **prompt:** refuse llmclient manifests the user may not read ([422e46c](https://github.com/smarter-sh/smarter/commit/422e46c06415d4af340102654ea08c5c30f23f4e))
- **static:** serve the console from the cdn once its build is uploaded ([94c0939](https://github.com/smarter-sh/smarter/commit/94c09397f6ef32069f69b1abd931c9386be3cf2d))

### Refactoring

- **account:** move sign-in to the console's api and pages ([705ea3f](https://github.com/smarter-sh/smarter/commit/705ea3f3a0936eb3820815a4cf2db164803e3773))
- **account:** move user menu endpoints to the account api ([99456cb](https://github.com/smarter-sh/smarter/commit/99456cb7f5e5bfbaa7aa97c12beee7de5985a225))
- **api:** serve openapi.json at /api/v1, sam kinds in the session ([cf1e86a](https://github.com/smarter-sh/smarter/commit/cf1e86a40a85088ff2fad6fac99c064533a055bf))
- **console:** add the sidebar and user menu to the console ([78bd921](https://github.com/smarter-sh/smarter/commit/78bd9214c281b1d38857855ac69ad66660663018))
- **console:** add welcome, tip and theme menu to the frame ([9b36b50](https://github.com/smarter-sh/smarter/commit/9b36b50ad099efad53dbe3cfb7b57b9b76d27224))
- **console:** remove smarter/react, now in smarter-console ([2b05713](https://github.com/smarter-sh/smarter/commit/2b05713b6c72b5e4b176453b2abac07c988de003))
- **console:** retire the django console frame and its tags ([396f06e](https://github.com/smarter-sh/smarter/commit/396f06e69526f76177f7f402ec9dea00a87c0601))
- **console:** serve every resource list from the console ([456ce0d](https://github.com/smarter-sh/smarter/commit/456ce0dc806d0374fbd5a48b565815b1323927a4))
- **console:** serve the dashboard from the single-page console ([8d50c2d](https://github.com/smarter-sh/smarter/commit/8d50c2d9905f08f7e3d4dea966261841656070a7))
- **console:** serve the drop zone, passthrough and terminal ([734ca05](https://github.com/smarter-sh/smarter/commit/734ca054dcf00c5472f557daaa48909410ffcddd))
- **console:** serve the manifest pages from the console ([bd41c29](https://github.com/smarter-sh/smarter/commit/bd41c294500bd85f328d81be23e31f1556e356f8))
- **console:** serve the sign-in pages from the single-page app ([9bbf7cb](https://github.com/smarter-sh/smarter/commit/9bbf7cb99bbe36abdbd1c5de80091a3f633709cc))
- **console:** serve the workbench and llmclient manifest page ([6482719](https://github.com/smarter-sh/smarter/commit/64827195541f4ae10394f01930a2d90a8c5b0973))
- **docs:** serve the docs pages from the console, publicly ([f41961a](https://github.com/smarter-sh/smarter/commit/f41961ac9ea15f1dc2e43dc8d7ecffcdd67bc8e8))
- **guardrail:** serve the Guardrail list from the console ([d2798db](https://github.com/smarter-sh/smarter/commit/d2798dbfd41d8efae2d1d848aebe72e65b5eebb5))
- **helm:** rename the api to smarter-api in Docker and Helm ([fb832e0](https://github.com/smarter-sh/smarter/commit/fb832e0c5a57a3c3f02f39cdb145154f87c31856))
- **llmtool:** serve the Extensions console from the console ([26bef19](https://github.com/smarter-sh/smarter/commit/26bef19c58ea6261b6585df46f4d082946d47a48))
- **prompt:** move the workbench's endpoints into the apis ([8a6b7f3](https://github.com/smarter-sh/smarter/commit/8a6b7f397f1cbc89e18acb8a964383cc15032881))
- **static:** serve static files from the cdn behind a setting ([ad29fb3](https://github.com/smarter-sh/smarter/commit/ad29fb303c689f56f6a8c59165d80b949ac7d51a))

## [0.43.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.11-alpha.2...v0.43.0-alpha.1) (2026-11-08)

### Features

- **api:** add the web console session api, GET /api/web/session/ ([5f48fa1](https://github.com/smarter-sh/smarter/commit/5f48fa111b7c966075754b5cfd5d4fba0b3c6117))
- **react:** add @smarter/console, the single-page web console ([6591148](https://github.com/smarter-sh/smarter/commit/659114897e502d78e5163cc837ec915b5bf97ac4))

### Bug Fixes

- **account:** send a test account's generated admin no welcome email ([026477b](https://github.com/smarter-sh/smarter/commit/026477bbdf9070c155224c654b04dfd7613a4791))
- **account:** show the console in the welcome email's graphic ([93f0b93](https://github.com/smarter-sh/smarter/commit/93f0b93bfdb855f3f01b26c8a3a08aa9a3436d21))
- **account:** verify email on sign-up, move account pages to console ([e96fc95](https://github.com/smarter-sh/smarter/commit/e96fc95754ee57504db979850b13a2897517486a))
- **dashboard:** give Budgets a read rule in the resource api ([3f5e6ac](https://github.com/smarter-sh/smarter/commit/3f5e6ac8d738191ac5ca187ad439253bf90ef46a))
- **dashboard:** serve the console without its splash to visitors ([6e654fa](https://github.com/smarter-sh/smarter/commit/6e654fa080a70ea5e032b6af8595ddc9a9fbf8a4))
- **mcpserver:** index smarter-console, and list its contract copies ([7477974](https://github.com/smarter-sh/smarter/commit/7477974e8be99095f2c8cae57760422482c6bcf6))
- **prompt:** refuse llmclient manifests the user may not read ([422e46c](https://github.com/smarter-sh/smarter/commit/422e46c06415d4af340102654ea08c5c30f23f4e))
- **static:** serve the console from the cdn once its build is uploaded ([94c0939](https://github.com/smarter-sh/smarter/commit/94c09397f6ef32069f69b1abd931c9386be3cf2d))

### Refactoring

- **account:** move sign-in to the console's api and pages ([705ea3f](https://github.com/smarter-sh/smarter/commit/705ea3f3a0936eb3820815a4cf2db164803e3773))
- **account:** move user menu endpoints to the account api ([99456cb](https://github.com/smarter-sh/smarter/commit/99456cb7f5e5bfbaa7aa97c12beee7de5985a225))
- **api:** serve openapi.json at /api/v1, sam kinds in the session ([cf1e86a](https://github.com/smarter-sh/smarter/commit/cf1e86a40a85088ff2fad6fac99c064533a055bf))
- **console:** add the sidebar and user menu to the console ([78bd921](https://github.com/smarter-sh/smarter/commit/78bd9214c281b1d38857855ac69ad66660663018))
- **console:** add welcome, tip and theme menu to the frame ([9b36b50](https://github.com/smarter-sh/smarter/commit/9b36b50ad099efad53dbe3cfb7b57b9b76d27224))
- **console:** remove smarter/react, now in smarter-console ([2b05713](https://github.com/smarter-sh/smarter/commit/2b05713b6c72b5e4b176453b2abac07c988de003))
- **console:** retire the django console frame and its tags ([396f06e](https://github.com/smarter-sh/smarter/commit/396f06e69526f76177f7f402ec9dea00a87c0601))
- **console:** serve every resource list from the console ([456ce0d](https://github.com/smarter-sh/smarter/commit/456ce0dc806d0374fbd5a48b565815b1323927a4))
- **console:** serve the dashboard from the single-page console ([8d50c2d](https://github.com/smarter-sh/smarter/commit/8d50c2d9905f08f7e3d4dea966261841656070a7))
- **console:** serve the drop zone, passthrough and terminal ([734ca05](https://github.com/smarter-sh/smarter/commit/734ca054dcf00c5472f557daaa48909410ffcddd))
- **console:** serve the manifest pages from the console ([bd41c29](https://github.com/smarter-sh/smarter/commit/bd41c294500bd85f328d81be23e31f1556e356f8))
- **console:** serve the sign-in pages from the single-page app ([9bbf7cb](https://github.com/smarter-sh/smarter/commit/9bbf7cb99bbe36abdbd1c5de80091a3f633709cc))
- **console:** serve the workbench and llmclient manifest page ([6482719](https://github.com/smarter-sh/smarter/commit/64827195541f4ae10394f01930a2d90a8c5b0973))
- **docs:** serve the docs pages from the console, publicly ([f41961a](https://github.com/smarter-sh/smarter/commit/f41961ac9ea15f1dc2e43dc8d7ecffcdd67bc8e8))
- **guardrail:** serve the Guardrail list from the console ([d2798db](https://github.com/smarter-sh/smarter/commit/d2798dbfd41d8efae2d1d848aebe72e65b5eebb5))
- **helm:** rename the api to smarter-api in Docker and Helm ([fb832e0](https://github.com/smarter-sh/smarter/commit/fb832e0c5a57a3c3f02f39cdb145154f87c31856))
- **llmtool:** serve the Extensions console from the console ([26bef19](https://github.com/smarter-sh/smarter/commit/26bef19c58ea6261b6585df46f4d082946d47a48))
- **prompt:** move the workbench's endpoints into the apis ([8a6b7f3](https://github.com/smarter-sh/smarter/commit/8a6b7f397f1cbc89e18acb8a964383cc15032881))
- **static:** serve static files from the cdn behind a setting ([ad29fb3](https://github.com/smarter-sh/smarter/commit/ad29fb303c689f56f6a8c59165d80b949ac7d51a))
