# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

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

## [0.45.3-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.45.2...v0.45.3-alpha.1) (2026-11-14)

### Bug Fixes

- **docs:** use docs.smarter.sh for the sitemap and canonical links ([f61e018](https://github.com/smarter-sh/smarter/commit/f61e018ddcd12c660fd83f4dcad49aba60908b47))

## [0.45.2](https://github.com/smarter-sh/smarter/compare/v0.45.1...v0.45.2) (2026-11-13)

### Bug Fixes

- bump smarter-console to v1.1.11 ([adf7336](https://github.com/smarter-sh/smarter/commit/adf73361bdb65a29f28150ddcdc5df1e2145d1d7))

## [0.45.2-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.45.1...v0.45.2-alpha.1) (2026-11-13)

### Bug Fixes

- bump smarter-console to v1.1.11 ([adf7336](https://github.com/smarter-sh/smarter/commit/adf73361bdb65a29f28150ddcdc5df1e2145d1d7))

## [0.45.1](https://github.com/smarter-sh/smarter/compare/v0.45.0...v0.45.1) (2026-11-13)

### Bug Fixes

- **account:** log a user's multiple UserProfiles at debug, not warning ([242dc22](https://github.com/smarter-sh/smarter/commit/242dc2217212862d0bc8c04ddb155bcd035b06cf)), closes [#996](https://github.com/smarter-sh/smarter/issues/996)
- bump smarter-console to 1.1.10 ([8e8635d](https://github.com/smarter-sh/smarter/commit/8e8635df47ad8c5509a8b0b705653f5f58b74214))

## [0.45.1-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.45.1-alpha.1...v0.45.1-alpha.2) (2026-11-13)

### Bug Fixes

- **account:** log a user's multiple UserProfiles at debug, not warning ([242dc22](https://github.com/smarter-sh/smarter/commit/242dc2217212862d0bc8c04ddb155bcd035b06cf)), closes [#996](https://github.com/smarter-sh/smarter/issues/996)

## [0.45.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.45.0...v0.45.1-alpha.1) (2026-11-13)

### Bug Fixes

- bump smarter-console to 1.1.10 ([8e8635d](https://github.com/smarter-sh/smarter/commit/8e8635df47ad8c5509a8b0b705653f5f58b74214))

## [0.45.0](https://github.com/smarter-sh/smarter/compare/v0.44.14...v0.45.0) (2026-11-13)

### Features

- **api:** add extensions, usage, data exports and vectorsearch runs ([b4bb7f9](https://github.com/smarter-sh/smarter/commit/b4bb7f98f0c7aadca82fe65d9a367adcf1a91e70))

### Bug Fixes

- **drf:** answer duplicate api key names with a 400, not a 500 ([9de0953](https://github.com/smarter-sh/smarter/commit/9de0953c48ffd73d3d72654933ea75a5eab22acf))
- make flake8 check pyflakes and pycodestyle, ratchet complexity ([2263448](https://github.com/smarter-sh/smarter/commit/2263448aa55bff2265e893117f06bc35a54ef879))
- **plugin:** require staticData in a static plugin manifest ([b17d70a](https://github.com/smarter-sh/smarter/commit/b17d70a7bcf629573a642c50699c28612ee5ca55))
- **prompt:** save a prompt's history before its response returns ([ff55272](https://github.com/smarter-sh/smarter/commit/ff552724ef6af0e0955be62fb9ade23ba34feeb0))
- type-check test bodies, and fix the bugs that mypy found ([90907dd](https://github.com/smarter-sh/smarter/commit/90907dd334ce1c3f0201fc57c174cb271297324e))

## [0.45.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.45.0-alpha.2...v0.45.0-alpha.3) (2026-11-13)

### Bug Fixes

- make flake8 check pyflakes and pycodestyle, ratchet complexity ([2263448](https://github.com/smarter-sh/smarter/commit/2263448aa55bff2265e893117f06bc35a54ef879))

## [0.45.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.45.0-alpha.1...v0.45.0-alpha.2) (2026-11-13)

### Bug Fixes

- **plugin:** require staticData in a static plugin manifest ([b17d70a](https://github.com/smarter-sh/smarter/commit/b17d70a7bcf629573a642c50699c28612ee5ca55))
- type-check test bodies, and fix the bugs that mypy found ([90907dd](https://github.com/smarter-sh/smarter/commit/90907dd334ce1c3f0201fc57c174cb271297324e))

## [0.45.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.44.14...v0.45.0-alpha.1) (2026-11-13)

### Features

- **api:** add extensions, usage, data exports and vectorsearch runs ([b4bb7f9](https://github.com/smarter-sh/smarter/commit/b4bb7f98f0c7aadca82fe65d9a367adcf1a91e70))

### Bug Fixes

- **drf:** answer duplicate api key names with a 400, not a 500 ([9de0953](https://github.com/smarter-sh/smarter/commit/9de0953c48ffd73d3d72654933ea75a5eab22acf))
- **prompt:** save a prompt's history before its response returns ([ff55272](https://github.com/smarter-sh/smarter/commit/ff552724ef6af0e0955be62fb9ade23ba34feeb0))
