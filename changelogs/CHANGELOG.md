# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.17.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.16.7-alpha.2...v0.17.0-alpha.1) (2026-10-03)

### Features

- edit, validate, save, clone and delete manifests in the web console's manifest editor ([b78b1d2](https://github.com/smarter-sh/smarter/commit/b78b1d200ac905d7a1aa3fb22ae2dd25b4e77e81))

## [0.16.7-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.16.7-alpha.1...v0.16.7-alpha.2) (2026-10-03)

### Bug Fixes

- color list view toolbar icons, gray out disabled toolbar buttons, and bump React package versions ([ba5d342](https://github.com/smarter-sh/smarter/commit/ba5d342acf1f1b4eb666a89b3ffb9035c7e6d301))

## [0.16.7-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.16.6...v0.16.7-alpha.1) (2026-10-03)

=======

## [0.16.7](https://github.com/smarter-sh/smarter/compare/v0.16.6...v0.16.7) (2026-10-03)

### Bug Fixes

- disable the delete button in list views when a resource cannot be deleted ([f8baeaa](https://github.com/smarter-sh/smarter/commit/f8baeaab40141be9617f732294ba13c004226ed6))

## [0.16.7](https://github.com/smarter-sh/smarter/compare/v0.16.6...v0.16.7) (2026-10-03)

### Bug Fixes

* disable the delete button in list views when a resource cannot be deleted ([f8baeaa](https://github.com/smarter-sh/smarter/commit/f8baeaab40141be9617f732294ba13c004226ed6))

## [0.16.6](https://github.com/smarter-sh/smarter/compare/v0.16.5...v0.16.6) (2026-10-03)

### Bug Fixes

- refuse to delete resources that other resources depend on ([c8e8b1d](https://github.com/smarter-sh/smarter/commit/c8e8b1d3659d384909f8d917d9a4b18f18b69dc6))

## [0.16.5](https://github.com/smarter-sh/smarter/compare/v0.16.4...v0.16.5) (2026-10-03)

### Bug Fixes

- use utf8mb4 for MariaDB databases and decouple init job from backup flag ([1d4fe11](https://github.com/smarter-sh/smarter/commit/1d4fe1159803a3621c50354362fc9946abda6475))

## [0.16.4](https://github.com/smarter-sh/smarter/compare/v0.16.3...v0.16.4) (2026-10-03)

### Bug Fixes

- revert sql service name change back to smarter-mariadb ([cf569bb](https://github.com/smarter-sh/smarter/commit/cf569bbf9cdb1adaefb71e0ce72cc7cce2f177a8))

## [0.16.3](https://github.com/smarter-sh/smarter/compare/v0.16.2...v0.16.3) (2026-10-02)

### Bug Fixes

- **tests:** run create_prompt_history inline in test_handler_gobstoppers ([be4974d](https://github.com/smarter-sh/smarter/commit/be4974ded1dc62b212fa097d09f4e81950fb0f60))

## [0.16.2](https://github.com/smarter-sh/smarter/compare/v0.16.1...v0.16.2) (2026-10-02)

### Bug Fixes

- **conf:** accept the default-enabled AWS regions when AWS is not reachable ([6ba1f38](https://github.com/smarter-sh/smarter/commit/6ba1f383476751c888792fa1c2b498ecb5612351))

## [0.16.1](https://github.com/smarter-sh/smarter/compare/v0.16.0...v0.16.1) (2026-10-02)

### Bug Fixes

- **tests:** make four CI-only test failures deterministic ([b26fadd](https://github.com/smarter-sh/smarter/commit/b26fadd39476ce8ff324290f911c1f578aebf99b))

## [0.16.0](https://github.com/smarter-sh/smarter/compare/v0.15.1...v0.16.0) (2026-10-02)

### Features

- **account:** enforce budgets on any resource, with Budget manifests and budget vs actual charts ([ab24142](https://github.com/smarter-sh/smarter/commit/ab24142d299c37a0b0719c9fe80b04d4b5fdda28))
- **console:** list LLMHostCompute in the web console, and fix the list pages' clone, rename and delete ([aaacc81](https://github.com/smarter-sh/smarter/commit/aaacc8194281851b593ca299b019e2217b062a27))
- **llmhost:** run open-weight LLMs on our own Kubernetes cluster ([e77b3f4](https://github.com/smarter-sh/smarter/commit/e77b3f484af6a145637e52cb07fbe754664b2398))
- **proxy:** pass requests through to LLM provider APIs, with API keys kept as Smarter Secrets ([07a4220](https://github.com/smarter-sh/smarter/commit/07a42204cdfb8e48f51cdaa92b873f6a7efcb619))
- **vectorstore:** manage RAG vector databases: self-hosted Qdrant, Qdrant Cloud and Pinecone ([b904c24](https://github.com/smarter-sh/smarter/commit/b904c24c4590f7e493e23b8ef57b45966afddaed))

### Bug Fixes

- annotation keys, scaffolded api viewsets, secret api, and remaining tests ([de2f3f7](https://github.com/smarter-sh/smarter/commit/de2f3f70b0bccf7e37603e1ca6e9c8f041200734))
- **react:** replace \_\_dirname in Vite configs, and fix the manifest.json path ([ef8929c](https://github.com/smarter-sh/smarter/commit/ef8929c6f62235ba46577d784d54d98b967546f6))

## [0.16.0-alpha.6](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.5...v0.16.0-alpha.6) (2026-10-02)

### Bug Fixes

- annotation keys, scaffolded api viewsets, secret api, and remaining tests ([de2f3f7](https://github.com/smarter-sh/smarter/commit/de2f3f70b0bccf7e37603e1ca6e9c8f041200734))

## [0.16.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.4...v0.16.0-alpha.5) (2026-10-02)

### Features

- **vectorstore:** manage RAG vector databases: self-hosted Qdrant, Qdrant Cloud and Pinecone ([b904c24](https://github.com/smarter-sh/smarter/commit/b904c24c4590f7e493e23b8ef57b45966afddaed))

## [0.16.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.3...v0.16.0-alpha.4) (2026-10-02)

### Bug Fixes

- **react:** replace \_\_dirname in Vite configs, and fix the manifest.json path ([ef8929c](https://github.com/smarter-sh/smarter/commit/ef8929c6f62235ba46577d784d54d98b967546f6))

## [0.16.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.2...v0.16.0-alpha.3) (2026-10-02)

### Features

- **account:** enforce budgets on any resource, with Budget manifests and budget vs actual charts ([ab24142](https://github.com/smarter-sh/smarter/commit/ab24142d299c37a0b0719c9fe80b04d4b5fdda28))

## [0.16.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.16.0-alpha.1...v0.16.0-alpha.2) (2026-10-01)

### Features

- **proxy:** pass requests through to LLM provider APIs, with API keys kept as Smarter Secrets ([07a4220](https://github.com/smarter-sh/smarter/commit/07a42204cdfb8e48f51cdaa92b873f6a7efcb619))

## [0.16.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.15.1...v0.16.0-alpha.1) (2026-10-01)

### Features

- **console:** list LLMHostCompute in the web console, and fix the list pages' clone, rename and delete ([aaacc81](https://github.com/smarter-sh/smarter/commit/aaacc8194281851b593ca299b019e2217b062a27))
- **llmhost:** run open-weight LLMs on our own Kubernetes cluster ([e77b3f4](https://github.com/smarter-sh/smarter/commit/e77b3f484af6a145637e52cb07fbe754664b2398))

## [0.15.1](https://github.com/smarter-sh/smarter/compare/v0.15.0...v0.15.1) (2026-10-01)

### Bug Fixes

- **react:** migrate to Vite 8/Oxc, update workspace deps, fix build script ([27da1ca](https://github.com/smarter-sh/smarter/commit/27da1cacff80bdc683dfe31825e532a7630adca9))

## [0.15.1-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.15.0...v0.15.1-alpha.1) (2026-10-01)

### Bug Fixes

- **react:** migrate to Vite 8/Oxc, update workspace deps, fix build script ([27da1ca](https://github.com/smarter-sh/smarter/commit/27da1cacff80bdc683dfe31825e532a7630adca9))

## [0.15.0](https://github.com/smarter-sh/smarter/compare/v0.14.22...v0.15.0) (2026-09-30)

### Features

- add addtl url endpoints ([a0e7399](https://github.com/smarter-sh/smarter/commit/a0e7399e7fab9b6987f18c83fe8ed9176e1806d1))
- create WorkbenchHelp common component ([7814812](https://github.com/smarter-sh/smarter/commit/7814812393e6ff1ff49c37a87ab216a858dc8ce9))
- **guardrail:** implement manifest-declared guardrails for LLM prompts ([329527e](https://github.com/smarter-sh/smarter/commit/329527e8e607a9adf830b71518e385f812d1b9f7))
- **llmclient:** add built-in LLMClients that combine plugins, MCPClients and guardrails ([168caae](https://github.com/smarter-sh/smarter/commit/168caaefaeba26034670ac53e2e0b74ff72071fe))
- **mcpclient:** add experimental MCPClient for remote Model Context Protocol servers ([86c0ecd](https://github.com/smarter-sh/smarter/commit/86c0ecdc9c88d3490f1d1e3a88df584a8f9ee77a))
- **plugin:** add experimental WebsearchPlugin for web search and reading web pages ([41caead](https://github.com/smarter-sh/smarter/commit/41caeada4f4cc1033941a36bdf6cb02d3cec5937))
- **plugin:** add SkillPlugin for Agent Skills (SKILL.md), verbatim or sourced from GitHub ([6acf1aa](https://github.com/smarter-sh/smarter/commit/6acf1aa28163b8079d22045326901d7723fb9205))
- scaffold guardrail app ([4f1778a](https://github.com/smarter-sh/smarter/commit/4f1778a01f8c97839bb799d9bf5c01af09801878))
- scaffold guardrail service ([db6405c](https://github.com/smarter-sh/smarter/commit/db6405c749f4f347bd03dd918e0b0fa5c2730483))
- scaffold LLMHost ([a109218](https://github.com/smarter-sh/smarter/commit/a109218b7e4c12889db66117055eccdf9713956d))
- scaffold MCPClient app ([7ebe7c4](https://github.com/smarter-sh/smarter/commit/7ebe7c47b5477dd919f27f0dbb06a42942af9ecd))
- scaffold Orchestrator ([091394f](https://github.com/smarter-sh/smarter/commit/091394f0d79821b294236fe6656e9c9937cba32b))
- scaffold SkillPlugin ([55df204](https://github.com/smarter-sh/smarter/commit/55df204517686553cb8c3503750f6d8dc0937d13))
- scaffold Vectorsearch ([9116df5](https://github.com/smarter-sh/smarter/commit/9116df5b791a91de1fdb269a5e0e010691cf16bc))
- setup WorkbenchHelp ([578f372](https://github.com/smarter-sh/smarter/commit/578f372b4a3fbb2eddcfb734838fca37bbd541cd))
- test built-in guardrails ([ff6955e](https://github.com/smarter-sh/smarter/commit/ff6955eed31c003399b429b8d6a9712f7ad81c67))
- WorkBench ([93a89f9](https://github.com/smarter-sh/smarter/commit/93a89f9e9064788c8ad21f97c70831fe1287ea0f))

### Bug Fixes

- add /api/v1/cli/resources/ ([d3c3325](https://github.com/smarter-sh/smarter/commit/d3c33250c2cdcbaa8fce46543a22818c555808be))
- add /api/v1/resources ([f837551](https://github.com/smarter-sh/smarter/commit/f837551ba4653cd8f1e0a05a565a2b5bdc92844d))
- add step 'Install MariaDB Connector/C' ([2ebcf64](https://github.com/smarter-sh/smarter/commit/2ebcf640aec9609a642813c83a8ce6c053c86d24))
- incorrect camel casing in to_snake_case() ([3a4f1f0](https://github.com/smarter-sh/smarter/commit/3a4f1f054511e68925f1eeab4efb2c27cd8f5abf))
- **plugin:** add tests for the plugin app's high level code, and fix the bugs they found ([6ed57ea](https://github.com/smarter-sh/smarter/commit/6ed57ea0060e7db0ee4ab3ce15dd2be902a5a86a))
- **plugin:** fix SQL injection, stale caches and manifest round trips in plugins ([533f0c5](https://github.com/smarter-sh/smarter/commit/533f0c54c421293a59bbdd94827d7b3abe83ee30))
- **plugin:** look up PluginDataBase by plugin FK, not by PluginMeta pk ([9a546e6](https://github.com/smarter-sh/smarter/commit/9a546e6793fe61163ee3e926a4b3553066947b46))
- **plugin:** make plugin selector search term matching whole-word, and typo tolerant ([e66b442](https://github.com/smarter-sh/smarter/commit/e66b442601e7bb8564c7b6f551771c79c6f7fd4b))
- remap Django ORM fields to Typescript type structs for listview ([05197c5](https://github.com/smarter-sh/smarter/commit/05197c5237b824518aa80e6c2d56dcaaf81f18e2))
- type hints ([630deda](https://github.com/smarter-sh/smarter/commit/630deda12a79107fa5116e79af12a9a0cd3af77a))

### Refactoring

- logging import ([6521f73](https://github.com/smarter-sh/smarter/commit/6521f739bedb5e37b19dbc5da565536c07b35e29))
- move contracts to the providers app ([0d2b3f7](https://github.com/smarter-sh/smarter/commit/0d2b3f7888d6ee0176cb169c14406516c1fcbe8d))
- move smarter-test-db into mariadb container ([6b1e8be](https://github.com/smarter-sh/smarter/commit/6b1e8bedc6e3b1b80af52e41499e85ef460a36c2))
- swap mysql for mariadb in local environment ([f8ad88e](https://github.com/smarter-sh/smarter/commit/f8ad88eb47f013c99d2b41e5ea494859a2860ad7))

## [0.15.0-alpha.28](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.27...v0.15.0-alpha.28) (2026-09-30)

### Bug Fixes

- incorrect camel casing in to_snake_case() ([3a4f1f0](https://github.com/smarter-sh/smarter/commit/3a4f1f054511e68925f1eeab4efb2c27cd8f5abf))

## [0.15.0-alpha.27](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.26...v0.15.0-alpha.27) (2026-09-30)

### Features

- **llmclient:** add built-in LLMClients that combine plugins, MCPClients and guardrails ([168caae](https://github.com/smarter-sh/smarter/commit/168caaefaeba26034670ac53e2e0b74ff72071fe))

## [0.15.0-alpha.26](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.25...v0.15.0-alpha.26) (2026-09-30)

### Bug Fixes

- remap Django ORM fields to Typescript type structs for listview ([05197c5](https://github.com/smarter-sh/smarter/commit/05197c5237b824518aa80e6c2d56dcaaf81f18e2))

## [0.15.0-alpha.25](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.24...v0.15.0-alpha.25) (2026-09-30)

### Bug Fixes

- swap sql.lawrencemcdaniel for smarter-mariadb ([581331b](https://github.com/smarter-sh/smarter/commit/581331b5640efa27872064c8296eaa255b793caf))

## [0.15.0-alpha.24](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.23...v0.15.0-alpha.24) (2026-09-30)

### Bug Fixes

- **plugin:** look up PluginDataBase by plugin FK, not by PluginMeta pk ([9a546e6](https://github.com/smarter-sh/smarter/commit/9a546e6793fe61163ee3e926a4b3553066947b46))

## [0.15.0-alpha.23](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.22...v0.15.0-alpha.23) (2026-09-30)

### Features

- **guardrail:** implement manifest-declared guardrails for LLM prompts ([329527e](https://github.com/smarter-sh/smarter/commit/329527e8e607a9adf830b71518e385f812d1b9f7))

## [0.15.0-alpha.22](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.21...v0.15.0-alpha.22) (2026-09-30)

### Bug Fixes

- type hints ([630deda](https://github.com/smarter-sh/smarter/commit/630deda12a79107fa5116e79af12a9a0cd3af77a))

## [0.15.0-alpha.21](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.20...v0.15.0-alpha.21) (2026-09-30)

### Features

- **mcpclient:** add experimental MCPClient for remote Model Context Protocol servers ([86c0ecd](https://github.com/smarter-sh/smarter/commit/86c0ecdc9c88d3490f1d1e3a88df584a8f9ee77a))

## [0.15.0-alpha.20](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.19...v0.15.0-alpha.20) (2026-09-30)

### Bug Fixes

- add step 'Install MariaDB Connector/C' ([2ebcf64](https://github.com/smarter-sh/smarter/commit/2ebcf640aec9609a642813c83a8ce6c053c86d24))

## [0.15.0-alpha.19](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.18...v0.15.0-alpha.19) (2026-09-30)

### Bug Fixes

- **plugin:** make plugin selector search term matching whole-word, and typo tolerant ([e66b442](https://github.com/smarter-sh/smarter/commit/e66b442601e7bb8564c7b6f551771c79c6f7fd4b))

## [0.15.0-alpha.18](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.17...v0.15.0-alpha.18) (2026-09-30)

### Bug Fixes

- **plugin:** add tests for the plugin app's high level code, and fix the bugs they found ([6ed57ea](https://github.com/smarter-sh/smarter/commit/6ed57ea0060e7db0ee4ab3ce15dd2be902a5a86a))

## [0.15.0-alpha.17](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.16...v0.15.0-alpha.17) (2026-09-30)

### Features

- **plugin:** add experimental WebsearchPlugin for web search and reading web pages ([41caead](https://github.com/smarter-sh/smarter/commit/41caeada4f4cc1033941a36bdf6cb02d3cec5937))

## [0.15.0-alpha.16](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.15...v0.15.0-alpha.16) (2026-09-30)

### Features

- **plugin:** add SkillPlugin for Agent Skills (SKILL.md), verbatim or sourced from GitHub ([6acf1aa](https://github.com/smarter-sh/smarter/commit/6acf1aa28163b8079d22045326901d7723fb9205))

## [0.15.0-alpha.15](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.14...v0.15.0-alpha.15) (2026-09-30)

### Bug Fixes

- **plugin:** fix SQL injection, stale caches and manifest round trips in plugins ([533f0c5](https://github.com/smarter-sh/smarter/commit/533f0c54c421293a59bbdd94827d7b3abe83ee30))

## [0.15.0-alpha.14](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.13...v0.15.0-alpha.14) (2026-09-28)

### Bug Fixes

- add /api/v1/cli/resources/ ([d3c3325](https://github.com/smarter-sh/smarter/commit/d3c33250c2cdcbaa8fce46543a22818c555808be))
- add /api/v1/resources ([f837551](https://github.com/smarter-sh/smarter/commit/f837551ba4653cd8f1e0a05a565a2b5bdc92844d))

### Refactoring

- move smarter-test-db into mariadb container ([6b1e8be](https://github.com/smarter-sh/smarter/commit/6b1e8bedc6e3b1b80af52e41499e85ef460a36c2))
- swap mysql for mariadb in local environment ([f8ad88e](https://github.com/smarter-sh/smarter/commit/f8ad88eb47f013c99d2b41e5ea494859a2860ad7))

## [0.15.0-alpha.13](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.12...v0.15.0-alpha.13) (2026-08-19)

### Bug Fixes

- broken reverse url for charges_api_url ([22dbac1](https://github.com/smarter-sh/smarter/commit/22dbac1f47baf73d4e7a5dd9d7c449175b95882e))

### Refactoring

- move contracts to the providers app ([0d2b3f7](https://github.com/smarter-sh/smarter/commit/0d2b3f7888d6ee0176cb169c14406516c1fcbe8d))

## [0.15.0-alpha.12](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.11...v0.15.0-alpha.12) (2026-07-13)

## [0.15.0-alpha.11](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.10...v0.15.0-alpha.11) (2026-07-12)

## [0.15.0-alpha.10](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.9...v0.15.0-alpha.10) (2026-07-09)

## [0.15.0-alpha.9](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.8...v0.15.0-alpha.9) (2026-07-08)

## [0.15.0-alpha.8](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.7...v0.15.0-alpha.8) (2026-07-08)

## [0.15.0-alpha.7](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.6...v0.15.0-alpha.7) (2026-07-07)

## [0.15.0-alpha.6](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.5...v0.15.0-alpha.6) (2026-07-07)

## [0.15.0-alpha.5](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.4...v0.15.0-alpha.5) (2026-07-07)

## [0.15.0-alpha.4](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.3...v0.15.0-alpha.4) (2026-07-07)

## [0.15.0-alpha.3](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.2...v0.15.0-alpha.3) (2026-07-07)

## [0.15.0-alpha.2](https://github.com/smarter-sh/smarter/compare/v0.15.0-alpha.1...v0.15.0-alpha.2) (2026-07-06)

## [0.15.0-alpha.1](https://github.com/smarter-sh/smarter/compare/v0.14.20-alpha.6...v0.15.0-alpha.1) (2026-07-06)
