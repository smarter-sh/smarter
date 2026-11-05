# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).



## [0.42.3-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.42.3-alpha.2...v0.42.3-alpha.3) (2026-11-05)

### Bug Fixes

* **drf:** keep yaml parser internals out of the 400 response ([d64c9f5](https://github.com/smarter-sh/smarter/commit/d64c9f5b4be814e7342a1950c4d1a7e0ba4b0cf5))

## [0.42.3-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.3-alpha.1...v0.42.3-alpha.2) (2026-11-05)

### Bug Fixes

* **lib:** cache only payment answers, wire drf permission classes ([3940f2b](https://github.com/smarter-sh/smarter/commit/3940f2b3860127fca78f02a616a18e1388afde80))

### Performance

* **lib:** fix stale caches, lighten broker dependency queries ([c2b5c40](https://github.com/smarter-sh/smarter/commit/c2b5c408dcba016a6f5e20b07e61046dc7782684))

## [0.42.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.2...v0.42.3-alpha.1) (2026-11-04)

### Bug Fixes

* **lib:** stop credential leaks, fix token expiry and json encoding ([17dcee1](https://github.com/smarter-sh/smarter/commit/17dcee1ad4fa2253a69843e0a8a885722f26dbad))

### Performance

* **lib:** authenticate api keys once per request, cut redis calls ([4719073](https://github.com/smarter-sh/smarter/commit/4719073fa759a72e4d3526f8279817130b518008))

## [0.42.2](https://github.com/smarter-sh/smarter/compare/v0.42.1...v0.42.2) (2026-11-04)

### Bug Fixes

* **mcpserver:** log a tool call's argument names at INFO, and its values only at DEBUG ([0490183](https://github.com/smarter-sh/smarter/commit/04901837d15b862e713ab6d78716f5d99e1197e4)), closes [#918](https://github.com/smarter-sh/smarter/issues/918)

### Performance

* **doodle:** read the theme catalog once and skip unneeded svg text ([1c9d3a8](https://github.com/smarter-sh/smarter/commit/1c9d3a83f89ce362fda40e949b9214d2ee54577a))

## [0.42.2-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.2-alpha.1...v0.42.2-alpha.2) (2026-11-04)

### Bug Fixes

* **mcpserver:** log a tool call's argument names at INFO, and its values only at DEBUG ([0490183](https://github.com/smarter-sh/smarter/commit/04901837d15b862e713ab6d78716f5d99e1197e4)), closes [#918](https://github.com/smarter-sh/smarter/issues/918)

## [0.42.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.1...v0.42.2-alpha.1) (2026-11-04)

### Performance

* **doodle:** read the theme catalog once and skip unneeded svg text ([1c9d3a8](https://github.com/smarter-sh/smarter/commit/1c9d3a83f89ce362fda40e949b9214d2ee54577a))

## [0.42.1](https://github.com/smarter-sh/smarter/compare/v0.42.0...v0.42.1) (2026-11-04)

### Bug Fixes

* **doodle:** link the AI credit's Learn how to the blog post ([f00ac5c](https://github.com/smarter-sh/smarter/commit/f00ac5cac5fb7d16859c239a9cbae491c428c6c7))

## [0.42.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.42.0...v0.42.1-alpha.1) (2026-11-04)

### Bug Fixes

* **doodle:** link the AI credit's Learn how to the blog post ([f00ac5c](https://github.com/smarter-sh/smarter/commit/f00ac5cac5fb7d16859c239a9cbae491c428c6c7))

## [0.42.0](https://github.com/smarter-sh/smarter/compare/v0.41.4...v0.42.0) (2026-11-04)

### Features

* **doodle:** add the sign-in page's doodle of the day ([0df9280](https://github.com/smarter-sh/smarter/commit/0df9280ff18c1155b6d1b8111a35dd42ec6d3302))
* **doodle:** let Smarter AI applications choose and draw the doodle ([d07b91f](https://github.com/smarter-sh/smarter/commit/d07b91f677ff0b8428ac36c62be9b5670f7492b1))
* **doodle:** let Smarter AI applications choose and draw the doodle ([a5b491b](https://github.com/smarter-sh/smarter/commit/a5b491b823119c4388309e39687ebe031c2b4ed4))
* **doodle:** let the doodle editor follow trends, and check its tone ([2e6cb08](https://github.com/smarter-sh/smarter/commit/2e6cb0806c126bcdf064f278d785f2901665aaa8))
* **doodle:** let the doodle editor follow trends, and check its tone ([210c935](https://github.com/smarter-sh/smarter/commit/210c9357e3744f0fb3f39620b84d05c580880dcd))

## [0.42.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.42.0-alpha.3...v0.42.0-alpha.4) (2026-11-04)

### Features

* **doodle:** let the doodle editor follow trends, and check its tone ([2e6cb08](https://github.com/smarter-sh/smarter/commit/2e6cb0806c126bcdf064f278d785f2901665aaa8))

## [0.42.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.42.0-alpha.2...v0.42.0-alpha.3) (2026-11-04)

### Features

* **doodle:** let the doodle editor follow trends, and check its tone ([210c935](https://github.com/smarter-sh/smarter/commit/210c9357e3744f0fb3f39620b84d05c580880dcd))

## [0.42.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.42.0-alpha.1...v0.42.0-alpha.2) (2026-11-04)

### Features

* **doodle:** let Smarter AI applications choose and draw the doodle ([d07b91f](https://github.com/smarter-sh/smarter/commit/d07b91f677ff0b8428ac36c62be9b5670f7492b1))
* **doodle:** let Smarter AI applications choose and draw the doodle ([a5b491b](https://github.com/smarter-sh/smarter/commit/a5b491b823119c4388309e39687ebe031c2b4ed4))

## [0.42.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.4...v0.42.0-alpha.1) (2026-11-03)

### Features

* **doodle:** add the sign-in page's doodle of the day ([0df9280](https://github.com/smarter-sh/smarter/commit/0df9280ff18c1155b6d1b8111a35dd42ec6d3302))

## [0.41.4](https://github.com/smarter-sh/smarter/compare/v0.41.3...v0.41.4) (2026-11-03)

### Bug Fixes

* **account:** merge users with the same email and make email unique ([c65bf6d](https://github.com/smarter-sh/smarter/commit/c65bf6dce8b98f17e349fd6ed0e0dcd66362251d)), closes [#914](https://github.com/smarter-sh/smarter/issues/914)
* **helm:** stop Alloy redacting Secret names, masks and code ([dd25f72](https://github.com/smarter-sh/smarter/commit/dd25f72dfad7749ef65075c89777d3e8c1c61857)), closes [#913](https://github.com/smarter-sh/smarter/issues/913) [#898](https://github.com/smarter-sh/smarter/issues/898) [#913](https://github.com/smarter-sh/smarter/issues/913)
* **infrastructure:** mask email recipients in the email service's and receivers' logs ([c8cd6af](https://github.com/smarter-sh/smarter/commit/c8cd6afc151f26a60685b0e66c94673c06ffba39)), closes [#911](https://github.com/smarter-sh/smarter/issues/911)
* link to docs.smarter.sh pages at their current urls ([d7cb479](https://github.com/smarter-sh/smarter/commit/d7cb479f1f77b3769abd467f8bb8e67d736c874f))

### Refactoring

* **mcpserver:** add a service layer, and stop naming two servers ([0005c29](https://github.com/smarter-sh/smarter/commit/0005c29a6bae2880311a9dbeddbd41e15261b41c))

## [0.41.4-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.41.4-alpha.3...v0.41.4-alpha.4) (2026-11-03)

### Bug Fixes

* **account:** merge users with the same email and make email unique ([c65bf6d](https://github.com/smarter-sh/smarter/commit/c65bf6dce8b98f17e349fd6ed0e0dcd66362251d)), closes [#914](https://github.com/smarter-sh/smarter/issues/914)

## [0.41.4-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.41.4-alpha.2...v0.41.4-alpha.3) (2026-11-03)

### Bug Fixes

* **helm:** stop Alloy redacting Secret names, masks and code ([dd25f72](https://github.com/smarter-sh/smarter/commit/dd25f72dfad7749ef65075c89777d3e8c1c61857)), closes [#913](https://github.com/smarter-sh/smarter/issues/913) [#898](https://github.com/smarter-sh/smarter/issues/898) [#913](https://github.com/smarter-sh/smarter/issues/913)

## [0.41.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.41.4-alpha.1...v0.41.4-alpha.2) (2026-11-03)

### Bug Fixes

* link to docs.smarter.sh pages at their current urls ([d7cb479](https://github.com/smarter-sh/smarter/commit/d7cb479f1f77b3769abd467f8bb8e67d736c874f))

## [0.41.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.3...v0.41.4-alpha.1) (2026-11-03)

### Bug Fixes

* **infrastructure:** mask email recipients in the email service's and receivers' logs ([c8cd6af](https://github.com/smarter-sh/smarter/commit/c8cd6afc151f26a60685b0e66c94673c06ffba39)), closes [#911](https://github.com/smarter-sh/smarter/issues/911)

### Refactoring

* **mcpserver:** add a service layer, and stop naming two servers ([0005c29](https://github.com/smarter-sh/smarter/commit/0005c29a6bae2880311a9dbeddbd41e15261b41c))

## [0.41.3](https://github.com/smarter-sh/smarter/compare/v0.41.2...v0.41.3) (2026-11-03)

### Bug Fixes

* **account:** one operation per line, docstrings, and type errors ([dcad675](https://github.com/smarter-sh/smarter/commit/dcad675fa00b417f79a30a9b498df86db0bcc26a))
* **api:** type the contract models, and regenerate the contract ([b128de5](https://github.com/smarter-sh/smarter/commit/b128de54d895bdb31d9139e339bd588e37d84350))
* **lib:** one operation per line, docstrings, and type errors ([8ad966a](https://github.com/smarter-sh/smarter/commit/8ad966a7b9dfe644d86b6033f7d76ed657c7449a))
* **llmclient:** one operation per line, docstrings, and type errors ([1ee6b1b](https://github.com/smarter-sh/smarter/commit/1ee6b1b0f202ca34891d207345a96904af7b7328))
* **llmtool:** one operation per line, docstrings, and type errors ([b04a67b](https://github.com/smarter-sh/smarter/commit/b04a67b12902b8a133c798801ccdc1c68013b09f))
* one operation per line, docstrings, and type errors in small apps ([7d5d5c0](https://github.com/smarter-sh/smarter/commit/7d5d5c0b1b9f071f3ac6209e4f167730f0736ea7))
* **provider:** one operation per line, docstrings, and type errors ([a8fbb19](https://github.com/smarter-sh/smarter/commit/a8fbb1948ddce8b5a2d87d35dfdaf0b96aa8fa82))
* **vectorstore:** one operation per line, docstrings, and type errors ([62f56ac](https://github.com/smarter-sh/smarter/commit/62f56aca00de97038b92a664e9257b906793e908))

### Refactoring

* **llmhost:** one operation per line, docstrings, and types ([ef75f02](https://github.com/smarter-sh/smarter/commit/ef75f02303e30631b0d9811d408d128ddc6b3766))

## [0.41.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.2...v0.41.3-alpha.1) (2026-11-03)

### Bug Fixes

* **account:** one operation per line, docstrings, and type errors ([dcad675](https://github.com/smarter-sh/smarter/commit/dcad675fa00b417f79a30a9b498df86db0bcc26a))
* **api:** type the contract models, and regenerate the contract ([b128de5](https://github.com/smarter-sh/smarter/commit/b128de54d895bdb31d9139e339bd588e37d84350))
* **lib:** one operation per line, docstrings, and type errors ([8ad966a](https://github.com/smarter-sh/smarter/commit/8ad966a7b9dfe644d86b6033f7d76ed657c7449a))
* **llmclient:** one operation per line, docstrings, and type errors ([1ee6b1b](https://github.com/smarter-sh/smarter/commit/1ee6b1b0f202ca34891d207345a96904af7b7328))
* **llmtool:** one operation per line, docstrings, and type errors ([b04a67b](https://github.com/smarter-sh/smarter/commit/b04a67b12902b8a133c798801ccdc1c68013b09f))
* one operation per line, docstrings, and type errors in small apps ([7d5d5c0](https://github.com/smarter-sh/smarter/commit/7d5d5c0b1b9f071f3ac6209e4f167730f0736ea7))
* **provider:** one operation per line, docstrings, and type errors ([a8fbb19](https://github.com/smarter-sh/smarter/commit/a8fbb1948ddce8b5a2d87d35dfdaf0b96aa8fa82))
* **vectorstore:** one operation per line, docstrings, and type errors ([62f56ac](https://github.com/smarter-sh/smarter/commit/62f56aca00de97038b92a664e9257b906793e908))

### Refactoring

* **llmhost:** one operation per line, docstrings, and types ([ef75f02](https://github.com/smarter-sh/smarter/commit/ef75f02303e30631b0d9811d408d128ddc6b3766))

## [0.41.2](https://github.com/smarter-sh/smarter/compare/v0.41.1...v0.41.2) (2026-11-03)

### Bug Fixes

* **provider:** retry without temperature when a model rejects it ([de0a446](https://github.com/smarter-sh/smarter/commit/de0a446e869c898be9b8226b5ffc5b2a77beb9d4))

## [0.41.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.1...v0.41.2-alpha.1) (2026-11-03)

### Bug Fixes

* **provider:** retry without temperature when a model rejects it ([de0a446](https://github.com/smarter-sh/smarter/commit/de0a446e869c898be9b8226b5ffc5b2a77beb9d4))

## [0.41.1](https://github.com/smarter-sh/smarter/compare/v0.41.0...v0.41.1) (2026-11-03)

### Bug Fixes

* **dashboard:** list the features of 0.30 to 0.41 in What's New ([34ce7de](https://github.com/smarter-sh/smarter/commit/34ce7de67fd11ad21a42fe30e1ea446e0c32ea09))
* **mcpserver:** serve platform staff only, and staff-only LLMClients ([7bac749](https://github.com/smarter-sh/smarter/commit/7bac749cdeb7692717780a48c14ea5f3faa52a1d))

## [0.41.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.41.1-alpha.1...v0.41.1-alpha.2) (2026-11-02)

### Bug Fixes

* **mcpserver:** serve platform staff only, and staff-only LLMClients ([7bac749](https://github.com/smarter-sh/smarter/commit/7bac749cdeb7692717780a48c14ea5f3faa52a1d))

## [0.41.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.0...v0.41.1-alpha.1) (2026-11-02)

### Bug Fixes

* **dashboard:** list the features of 0.30 to 0.41 in What's New ([34ce7de](https://github.com/smarter-sh/smarter/commit/34ce7de67fd11ad21a42fe30e1ea446e0c32ea09))

## [0.41.0](https://github.com/smarter-sh/smarter/compare/v0.40.5...v0.41.0) (2026-11-02)

### Features

* **mcpserver:** add a staff-only operations server for pod logs ([c5d5e05](https://github.com/smarter-sh/smarter/commit/c5d5e05f53e574cd89a154aca2a243d3b15d08b8))
* **mcpserver:** add platform_status and eks_status operations tools ([c4cf86a](https://github.com/smarter-sh/smarter/commit/c4cf86af25114dbc7cc1d20a1aa460af56b6a335))
* **mcpserver:** add user_support_snapshot and check_reply tools ([223268c](https://github.com/smarter-sh/smarter/commit/223268c5b28a4027b6d1be6a7834d52a8cf0396d))

### Refactoring

* **mcpserver:** one operation per line, and full docstrings ([c5e0fb0](https://github.com/smarter-sh/smarter/commit/c5e0fb026305a97786bedb6c11ef53bbb7fd1be6))

## [0.41.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.41.0-alpha.2...v0.41.0-alpha.3) (2026-11-02)

### Features

* **mcpserver:** add user_support_snapshot and check_reply tools ([223268c](https://github.com/smarter-sh/smarter/commit/223268c5b28a4027b6d1be6a7834d52a8cf0396d))

## [0.41.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.41.0-alpha.1...v0.41.0-alpha.2) (2026-11-02)

### Features

* **mcpserver:** add platform_status and eks_status operations tools ([c4cf86a](https://github.com/smarter-sh/smarter/commit/c4cf86af25114dbc7cc1d20a1aa460af56b6a335))

## [0.41.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.5...v0.41.0-alpha.1) (2026-11-02)

### Features

* **mcpserver:** add a staff-only operations server for pod logs ([c5d5e05](https://github.com/smarter-sh/smarter/commit/c5d5e05f53e574cd89a154aca2a243d3b15d08b8))

## [0.40.5](https://github.com/smarter-sh/smarter/compare/v0.40.4...v0.40.5) (2026-11-02)

### Bug Fixes

* **account:** add a Slack invitation email and an unsubscribe link ([1fb9f1d](https://github.com/smarter-sh/smarter/commit/1fb9f1ddb42553ac94063a7e7cc15be4453647d2))
* **journal:** log 4xx error responses at WARNING without stack trace ([62d64a1](https://github.com/smarter-sh/smarter/commit/62d64a15bb32c7d5dbaab109bcffe42f34504e59)), closes [#897](https://github.com/smarter-sh/smarter/issues/897)
* **middleware:** don't log the client's IP address on a throttled request ([df41d14](https://github.com/smarter-sh/smarter/commit/df41d146dbf6094281cb9e6a3718b1f39de22947)), closes [#896](https://github.com/smarter-sh/smarter/issues/896)
* **prompt:** truncate a long User-Agent to Prompt.user_agent's length ([e02f695](https://github.com/smarter-sh/smarter/commit/e02f6951b450b4d3fa72fad93dba1cdf921a6675)), closes [#895](https://github.com/smarter-sh/smarter/issues/895)

## [0.40.5-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.40.5-alpha.2...v0.40.5-alpha.3) (2026-11-02)

### Bug Fixes

* **journal:** log 4xx error responses at WARNING without stack trace ([62d64a1](https://github.com/smarter-sh/smarter/commit/62d64a15bb32c7d5dbaab109bcffe42f34504e59)), closes [#897](https://github.com/smarter-sh/smarter/issues/897)

## [0.40.5-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.40.5-alpha.1...v0.40.5-alpha.2) (2026-11-02)

### Bug Fixes

* **middleware:** don't log the client's IP address on a throttled request ([df41d14](https://github.com/smarter-sh/smarter/commit/df41d146dbf6094281cb9e6a3718b1f39de22947)), closes [#896](https://github.com/smarter-sh/smarter/issues/896)
* **prompt:** truncate a long User-Agent to Prompt.user_agent's length ([e02f695](https://github.com/smarter-sh/smarter/commit/e02f6951b450b4d3fa72fad93dba1cdf921a6675)), closes [#895](https://github.com/smarter-sh/smarter/issues/895)

## [0.40.5-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.4...v0.40.5-alpha.1) (2026-11-02)

### Bug Fixes

* **account:** add a Slack invitation email and an unsubscribe link ([1fb9f1d](https://github.com/smarter-sh/smarter/commit/1fb9f1ddb42553ac94063a7e7cc15be4453647d2))

## [0.40.4](https://github.com/smarter-sh/smarter/compare/v0.40.3...v0.40.4) (2026-11-01)

### Bug Fixes

* **annotation:** invalidate cached annotations, prefetch them per page ([cb6bfcf](https://github.com/smarter-sh/smarter/commit/cb6bfcf818f3af8a86f1691006c81e5c71dc91d4))
* **blog:** announce release posts in Slack [#announcements](https://github.com/smarter-sh/smarter/issues/announcements), not [#general](https://github.com/smarter-sh/smarter/issues/general) ([8be14ed](https://github.com/smarter-sh/smarter/commit/8be14edecaa8cf8f388e850fd4abb65c9ffb4eae))
* **csrf:** renew the csrftoken cookie on console pages, name CSRF 403s ([df08a9f](https://github.com/smarter-sh/smarter/commit/df08a9f22334794560d80e48beffa7068402294c)), closes [#885](https://github.com/smarter-sh/smarter/issues/885)
* **prompt:** redirect a signed-out visitor of the workbench to sign-in instead of a 403 ([5dd01b0](https://github.com/smarter-sh/smarter/commit/5dd01b0c47e12e3ebca7e208667bd35f967f2edb)), closes [#886](https://github.com/smarter-sh/smarter/issues/886)

## [0.40.4-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.40.4-alpha.3...v0.40.4-alpha.4) (2026-11-01)

### Bug Fixes

* **csrf:** renew the csrftoken cookie on console pages, name CSRF 403s ([df08a9f](https://github.com/smarter-sh/smarter/commit/df08a9f22334794560d80e48beffa7068402294c)), closes [#885](https://github.com/smarter-sh/smarter/issues/885)

## [0.40.4-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.40.4-alpha.2...v0.40.4-alpha.3) (2026-11-01)

### Bug Fixes

* **annotation:** invalidate cached annotations, prefetch them per page ([cb6bfcf](https://github.com/smarter-sh/smarter/commit/cb6bfcf818f3af8a86f1691006c81e5c71dc91d4))

## [0.40.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.40.4-alpha.1...v0.40.4-alpha.2) (2026-11-01)

### Bug Fixes

* **prompt:** redirect a signed-out visitor of the workbench to sign-in instead of a 403 ([5dd01b0](https://github.com/smarter-sh/smarter/commit/5dd01b0c47e12e3ebca7e208667bd35f967f2edb)), closes [#886](https://github.com/smarter-sh/smarter/issues/886)

## [0.40.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.3...v0.40.4-alpha.1) (2026-11-01)

### Bug Fixes

* **blog:** announce release posts in Slack [#announcements](https://github.com/smarter-sh/smarter/issues/announcements), not [#general](https://github.com/smarter-sh/smarter/issues/general) ([8be14ed](https://github.com/smarter-sh/smarter/commit/8be14edecaa8cf8f388e850fd4abb65c9ffb4eae))

## [0.40.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.2...v0.40.3-alpha.1) (2026-10-31)

### Bug Fixes

- **docker:** make code root-owned and pod filesystems read-only ([b94979d](https://github.com/smarter-sh/smarter/commit/b94979d63d2706bc9a1a847e9a42bb78fe4017b0))

## [0.40.2](https://github.com/smarter-sh/smarter/compare/v0.40.1...v0.40.2) (2026-10-31)

### Bug Fixes

- **account:** delete retired example resources at initialization ([6fc5bdc](https://github.com/smarter-sh/smarter/commit/6fc5bdc445fd7866c0e9dc6ca3c873fd1762b0be)), closes [#882](https://github.com/smarter-sh/smarter/issues/882)

## [0.40.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.1...v0.40.2-alpha.1) (2026-10-31)

### Bug Fixes

- **account:** delete retired example resources at initialization ([6fc5bdc](https://github.com/smarter-sh/smarter/commit/6fc5bdc445fd7866c0e9dc6ca3c873fd1762b0be)), closes [#882](https://github.com/smarter-sh/smarter/issues/882)

## [0.40.1](https://github.com/smarter-sh/smarter/compare/v0.40.0...v0.40.1) (2026-10-31)

### Bug Fixes

- **infrastructure:** post the init and backup job logs to Slack ([7d12824](https://github.com/smarter-sh/smarter/commit/7d12824f8830f876aeeae35edc379088068a72e6))

## [0.40.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.0...v0.40.1-alpha.1) (2026-10-31)

### Bug Fixes

- **infrastructure:** post the init and backup job logs to Slack ([7d12824](https://github.com/smarter-sh/smarter/commit/7d12824f8830f876aeeae35edc379088068a72e6))

## [0.40.0](https://github.com/smarter-sh/smarter/compare/v0.39.2...v0.40.0) (2026-10-31)

### Features

- **mcpserver:** add GitHub issue tools and manifest validation ([5a33702](https://github.com/smarter-sh/smarter/commit/5a33702b058a49fdb42b9b12673c62c2a1a02cc3))
- **mcpserver:** add pull request, issue reading and closing tools ([b70bd52](https://github.com/smarter-sh/smarter/commit/b70bd52bb5ba69d77aa2e37ab43880a478769277))

### Bug Fixes

- **middleware:** answer blocked paths 404, throttled clients 429 ([411e11b](https://github.com/smarter-sh/smarter/commit/411e11b4164ae78b8e4547316de51c17b6113f85))

## [0.40.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.40.0-alpha.1...v0.40.0-alpha.2) (2026-10-31)

### Features

- **mcpserver:** add pull request, issue reading and closing tools ([b70bd52](https://github.com/smarter-sh/smarter/commit/b70bd52bb5ba69d77aa2e37ab43880a478769277))

## [0.40.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.39.2...v0.40.0-alpha.1) (2026-10-31)

### Features

- **mcpserver:** add GitHub issue tools and manifest validation ([5a33702](https://github.com/smarter-sh/smarter/commit/5a33702b058a49fdb42b9b12673c62c2a1a02cc3))

### Bug Fixes

- **middleware:** answer blocked paths 404, throttled clients 429 ([411e11b](https://github.com/smarter-sh/smarter/commit/411e11b4164ae78b8e4547316de51c17b6113f85))
