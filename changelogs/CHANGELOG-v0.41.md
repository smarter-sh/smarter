# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.41.4](https://github.com/smarter-sh/smarter/compare/v0.41.3...v0.41.4) (2026-11-03)

### Bug Fixes

- **account:** merge users with the same email and make email unique ([c65bf6d](https://github.com/smarter-sh/smarter/commit/c65bf6dce8b98f17e349fd6ed0e0dcd66362251d)), closes [#914](https://github.com/smarter-sh/smarter/issues/914)
- **helm:** stop Alloy redacting Secret names, masks and code ([dd25f72](https://github.com/smarter-sh/smarter/commit/dd25f72dfad7749ef65075c89777d3e8c1c61857)), closes [#913](https://github.com/smarter-sh/smarter/issues/913) [#898](https://github.com/smarter-sh/smarter/issues/898) [#913](https://github.com/smarter-sh/smarter/issues/913)
- **infrastructure:** mask email recipients in the email service's and receivers' logs ([c8cd6af](https://github.com/smarter-sh/smarter/commit/c8cd6afc151f26a60685b0e66c94673c06ffba39)), closes [#911](https://github.com/smarter-sh/smarter/issues/911)
- link to docs.smarter.sh pages at their current urls ([d7cb479](https://github.com/smarter-sh/smarter/commit/d7cb479f1f77b3769abd467f8bb8e67d736c874f))

### Refactoring

- **mcpserver:** add a service layer, and stop naming two servers ([0005c29](https://github.com/smarter-sh/smarter/commit/0005c29a6bae2880311a9dbeddbd41e15261b41c))

## [0.41.4-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.41.4-alpha.3...v0.41.4-alpha.4) (2026-11-03)

### Bug Fixes

- **account:** merge users with the same email and make email unique ([c65bf6d](https://github.com/smarter-sh/smarter/commit/c65bf6dce8b98f17e349fd6ed0e0dcd66362251d)), closes [#914](https://github.com/smarter-sh/smarter/issues/914)

## [0.41.4-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.41.4-alpha.2...v0.41.4-alpha.3) (2026-11-03)

### Bug Fixes

- **helm:** stop Alloy redacting Secret names, masks and code ([dd25f72](https://github.com/smarter-sh/smarter/commit/dd25f72dfad7749ef65075c89777d3e8c1c61857)), closes [#913](https://github.com/smarter-sh/smarter/issues/913) [#898](https://github.com/smarter-sh/smarter/issues/898) [#913](https://github.com/smarter-sh/smarter/issues/913)

## [0.41.4-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.41.4-alpha.1...v0.41.4-alpha.2) (2026-11-03)

### Bug Fixes

- link to docs.smarter.sh pages at their current urls ([d7cb479](https://github.com/smarter-sh/smarter/commit/d7cb479f1f77b3769abd467f8bb8e67d736c874f))

## [0.41.4-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.3...v0.41.4-alpha.1) (2026-11-03)

### Bug Fixes

- **infrastructure:** mask email recipients in the email service's and receivers' logs ([c8cd6af](https://github.com/smarter-sh/smarter/commit/c8cd6afc151f26a60685b0e66c94673c06ffba39)), closes [#911](https://github.com/smarter-sh/smarter/issues/911)

### Refactoring

- **mcpserver:** add a service layer, and stop naming two servers ([0005c29](https://github.com/smarter-sh/smarter/commit/0005c29a6bae2880311a9dbeddbd41e15261b41c))

## [0.41.3](https://github.com/smarter-sh/smarter/compare/v0.41.2...v0.41.3) (2026-11-03)

### Bug Fixes

- **account:** one operation per line, docstrings, and type errors ([dcad675](https://github.com/smarter-sh/smarter/commit/dcad675fa00b417f79a30a9b498df86db0bcc26a))
- **api:** type the contract models, and regenerate the contract ([b128de5](https://github.com/smarter-sh/smarter/commit/b128de54d895bdb31d9139e339bd588e37d84350))
- **lib:** one operation per line, docstrings, and type errors ([8ad966a](https://github.com/smarter-sh/smarter/commit/8ad966a7b9dfe644d86b6033f7d76ed657c7449a))
- **llmclient:** one operation per line, docstrings, and type errors ([1ee6b1b](https://github.com/smarter-sh/smarter/commit/1ee6b1b0f202ca34891d207345a96904af7b7328))
- **llmtool:** one operation per line, docstrings, and type errors ([b04a67b](https://github.com/smarter-sh/smarter/commit/b04a67b12902b8a133c798801ccdc1c68013b09f))
- one operation per line, docstrings, and type errors in small apps ([7d5d5c0](https://github.com/smarter-sh/smarter/commit/7d5d5c0b1b9f071f3ac6209e4f167730f0736ea7))
- **provider:** one operation per line, docstrings, and type errors ([a8fbb19](https://github.com/smarter-sh/smarter/commit/a8fbb1948ddce8b5a2d87d35dfdaf0b96aa8fa82))
- **vectorstore:** one operation per line, docstrings, and type errors ([62f56ac](https://github.com/smarter-sh/smarter/commit/62f56aca00de97038b92a664e9257b906793e908))

### Refactoring

- **llmhost:** one operation per line, docstrings, and types ([ef75f02](https://github.com/smarter-sh/smarter/commit/ef75f02303e30631b0d9811d408d128ddc6b3766))

## [0.41.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.2...v0.41.3-alpha.1) (2026-11-03)

### Bug Fixes

- **account:** one operation per line, docstrings, and type errors ([dcad675](https://github.com/smarter-sh/smarter/commit/dcad675fa00b417f79a30a9b498df86db0bcc26a))
- **api:** type the contract models, and regenerate the contract ([b128de5](https://github.com/smarter-sh/smarter/commit/b128de54d895bdb31d9139e339bd588e37d84350))
- **lib:** one operation per line, docstrings, and type errors ([8ad966a](https://github.com/smarter-sh/smarter/commit/8ad966a7b9dfe644d86b6033f7d76ed657c7449a))
- **llmclient:** one operation per line, docstrings, and type errors ([1ee6b1b](https://github.com/smarter-sh/smarter/commit/1ee6b1b0f202ca34891d207345a96904af7b7328))
- **llmtool:** one operation per line, docstrings, and type errors ([b04a67b](https://github.com/smarter-sh/smarter/commit/b04a67b12902b8a133c798801ccdc1c68013b09f))
- one operation per line, docstrings, and type errors in small apps ([7d5d5c0](https://github.com/smarter-sh/smarter/commit/7d5d5c0b1b9f071f3ac6209e4f167730f0736ea7))
- **provider:** one operation per line, docstrings, and type errors ([a8fbb19](https://github.com/smarter-sh/smarter/commit/a8fbb1948ddce8b5a2d87d35dfdaf0b96aa8fa82))
- **vectorstore:** one operation per line, docstrings, and type errors ([62f56ac](https://github.com/smarter-sh/smarter/commit/62f56aca00de97038b92a664e9257b906793e908))

### Refactoring

- **llmhost:** one operation per line, docstrings, and types ([ef75f02](https://github.com/smarter-sh/smarter/commit/ef75f02303e30631b0d9811d408d128ddc6b3766))

## [0.41.2](https://github.com/smarter-sh/smarter/compare/v0.41.1...v0.41.2) (2026-11-03)

### Bug Fixes

- **provider:** retry without temperature when a model rejects it ([de0a446](https://github.com/smarter-sh/smarter/commit/de0a446e869c898be9b8226b5ffc5b2a77beb9d4))

## [0.41.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.1...v0.41.2-alpha.1) (2026-11-03)

### Bug Fixes

- **provider:** retry without temperature when a model rejects it ([de0a446](https://github.com/smarter-sh/smarter/commit/de0a446e869c898be9b8226b5ffc5b2a77beb9d4))

## [0.41.1](https://github.com/smarter-sh/smarter/compare/v0.41.0...v0.41.1) (2026-11-03)

### Bug Fixes

- **dashboard:** list the features of 0.30 to 0.41 in What's New ([34ce7de](https://github.com/smarter-sh/smarter/commit/34ce7de67fd11ad21a42fe30e1ea446e0c32ea09))
- **mcpserver:** serve platform staff only, and staff-only LLMClients ([7bac749](https://github.com/smarter-sh/smarter/commit/7bac749cdeb7692717780a48c14ea5f3faa52a1d))

## [0.41.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.41.1-alpha.1...v0.41.1-alpha.2) (2026-11-02)

### Bug Fixes

- **mcpserver:** serve platform staff only, and staff-only LLMClients ([7bac749](https://github.com/smarter-sh/smarter/commit/7bac749cdeb7692717780a48c14ea5f3faa52a1d))

## [0.41.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.41.0...v0.41.1-alpha.1) (2026-11-02)

### Bug Fixes

- **dashboard:** list the features of 0.30 to 0.41 in What's New ([34ce7de](https://github.com/smarter-sh/smarter/commit/34ce7de67fd11ad21a42fe30e1ea446e0c32ea09))

## [0.41.0](https://github.com/smarter-sh/smarter/compare/v0.40.5...v0.41.0) (2026-11-02)

### Features

- **mcpserver:** add a staff-only operations server for pod logs ([c5d5e05](https://github.com/smarter-sh/smarter/commit/c5d5e05f53e574cd89a154aca2a243d3b15d08b8))
- **mcpserver:** add platform_status and eks_status operations tools ([c4cf86a](https://github.com/smarter-sh/smarter/commit/c4cf86af25114dbc7cc1d20a1aa460af56b6a335))
- **mcpserver:** add user_support_snapshot and check_reply tools ([223268c](https://github.com/smarter-sh/smarter/commit/223268c5b28a4027b6d1be6a7834d52a8cf0396d))

### Refactoring

- **mcpserver:** one operation per line, and full docstrings ([c5e0fb0](https://github.com/smarter-sh/smarter/commit/c5e0fb026305a97786bedb6c11ef53bbb7fd1be6))

## [0.41.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.41.0-alpha.2...v0.41.0-alpha.3) (2026-11-02)

### Features

- **mcpserver:** add user_support_snapshot and check_reply tools ([223268c](https://github.com/smarter-sh/smarter/commit/223268c5b28a4027b6d1be6a7834d52a8cf0396d))

## [0.41.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.41.0-alpha.1...v0.41.0-alpha.2) (2026-11-02)

### Features

- **mcpserver:** add platform_status and eks_status operations tools ([c4cf86a](https://github.com/smarter-sh/smarter/commit/c4cf86af25114dbc7cc1d20a1aa460af56b6a335))

## [0.41.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.40.5...v0.41.0-alpha.1) (2026-11-02)

### Features

- **mcpserver:** add a staff-only operations server for pod logs ([c5d5e05](https://github.com/smarter-sh/smarter/commit/c5d5e05f53e574cd89a154aca2a243d3b15d08b8))
